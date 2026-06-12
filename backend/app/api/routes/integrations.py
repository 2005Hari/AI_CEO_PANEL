# backend/app/api/routes/integrations.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, Integration, Document, Memory
from app.services.embeddings import embeddings_service

router = APIRouter()

class ConnectRequest(BaseModel):
    config: Dict[str, Any] = {}

class IntegrationResponse(BaseModel):
    id: Optional[str] = None
    project_id: str
    provider: str
    status: str
    config: Dict[str, Any] = {}
    connected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Supported list of provider names
SUPPORTED_PROVIDERS = ["slack", "github", "vercel", "google", "hubspot", "stripe"]

@router.get("/projects/{project_id}/integrations", response_model=List[IntegrationResponse])
async def list_integrations(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns integration connection status for all supported providers.
    If a provider is not in the database, it returns a disconnected stub.
    """
    result = await db.execute(select(Integration).where(Integration.project_id == project.id))
    db_integrations = result.scalars().all()
    
    integration_map = {i.provider: i for i in db_integrations}
    
    response_list = []
    for provider in SUPPORTED_PROVIDERS:
        if provider in integration_map:
            response_list.append(integration_map[provider])
        else:
            # Return a disconnected stub
            response_list.append(
                IntegrationResponse(
                    project_id=project.id,
                    provider=provider,
                    status="disconnected",
                    config={}
                )
            )
            
    return response_list


@router.post("/projects/{project_id}/integrations/{provider}/connect", response_model=IntegrationResponse)
async def connect_integration(
    provider: str,
    req: ConnectRequest,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect or update credentials for an integration provider.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported provider: {provider}")

    result = await db.execute(
        select(Integration)
        .where(Integration.project_id == project.id)
        .where(Integration.provider == provider)
    )
    db_int = result.scalars().first()

    if not db_int:
        db_int = Integration(
            project_id=project.id,
            provider=provider,
            status="connected",
            config=req.config,
            connected_at=datetime.utcnow()
        )
        db.add(db_int)
    else:
        db_int.status = "connected"
        db_int.config = req.config
        db_int.connected_at = datetime.utcnow()
        
    await db.commit()
    await db.refresh(db_int)
    return db_int


@router.delete("/projects/{project_id}/integrations/{provider}/disconnect", response_model=IntegrationResponse)
async def disconnect_integration(
    provider: str,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnects/removes an integration provider.
    """
    result = await db.execute(
        select(Integration)
        .where(Integration.project_id == project.id)
        .where(Integration.provider == provider)
    )
    db_int = result.scalars().first()

    if not db_int:
        return IntegrationResponse(
            project_id=project.id,
            provider=provider,
            status="disconnected",
            config={}
        )
        
    db_int.status = "disconnected"
    db_int.config = {}
    db_int.connected_at = None
    
    await db.commit()
    await db.refresh(db_int)
    return db_int


@router.post("/projects/{project_id}/integrations/{provider}/sync")
async def sync_integration(
    provider: str,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulates syncing data from an integration provider.
    Injects mock document/knowledge context into the project's RAG system.
    """
    project_id = project.id
    result = await db.execute(
        select(Integration)
        .where(Integration.project_id == project.id)
        .where(Integration.provider == provider)
        .where(Integration.status == "connected")
    )
    db_int = result.scalars().first()
    if not db_int:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Integration is not connected")

    # Create mock synced document content based on provider type
    sync_docs = []
    if provider == "github":
        sync_docs = [
            ("github_readme.md", "Project Repository Overview:\nThis project implements a next-generation automated SaaS boardroom orchestrator using Python and TypeScript. Deployment is managed via Vercel."),
            ("github_issues.md", "Active GitHub Issues:\n- Issue #12: Performance bottlenecks in dynamic WebSocket streams. Status: In Progress.\n- Issue #25: Enhance UX for credentials handling. Status: Triage.")
        ]
    elif provider == "slack":
        sync_docs = [
            ("slack_channel_logs.md", "Slack Conversation Logs (#general):\n[10:00 AM] CEO: We need to finalize the pricing plans for the B2B SaaS offer.\n[10:15 AM] CTO: Node performance is stable, but we need more tests.")
        ]
    else:
        sync_docs = [
            (f"{provider}_sync_data.txt", f"Mock synced content from external {provider} service. Synced successfully at {datetime.utcnow().isoformat()}.")
        ]

    synced_filenames = []
    for filename, content in sync_docs:
        # 1. Create mock document
        doc = Document(project_id=project_id, filename=f"[SYNC] {filename}")
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # 2. Embed content
        try:
            vector = await embeddings_service.embed_query(content)
            memory = Memory(
                project_id=project_id,
                document_id=doc.id,
                content=content,
                embedding=vector
            )
            db.add(memory)
            await db.commit()
            synced_filenames.append(filename)
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Mock RAG sync failed during embedding: {str(e)}"
            )

    return {
        "status": "success",
        "message": f"Successfully synced external {provider} logs/files into RAG knowledge base",
        "synced_files": synced_filenames,
        "synced_at": datetime.utcnow().isoformat()
    }
