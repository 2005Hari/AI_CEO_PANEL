# backend/app/api/routes/documents.py
import io
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.api.deps.project import get_project_for_user, get_document_for_user
from app.db.session import get_db
from app.db.models import Project, Document, Memory
from app.services.embeddings import embeddings_service

router = APIRouter()

# Pydantic schemas
class DocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/projects/{project_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all uploaded documents for a project."""
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project.id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    return documents

@router.post("/projects/{project_id}/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests text, markdown, or PDF documents, splits them recursively,
    generates embeddings, and stores them in the database.
    """
    project_id = project.id
    filename = file.filename
    content_type = file.content_type
    
    # 2. Extract text based on file format
    file_bytes = await file.read()
    raw_text = ""

    if filename.lower().endswith(".pdf") or content_type == "application/pdf":
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PdfReader(pdf_file)
            page_texts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    page_texts.append(text)
            raw_text = "\n".join(page_texts)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF file: {str(e)}"
            )
    elif filename.lower().endswith((".txt", ".md")) or "text" in str(content_type):
        try:
            raw_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                # Try fallback encoding
                raw_text = file_bytes.decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to decode text file. Ensure UTF-8 or Latin-1 encoding."
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only .txt, .md, and .pdf files are supported."
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text content is empty."
        )

    # 3. Split text recursively
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(raw_text)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text chunks generated."
        )

    # 4. Generate embeddings for all chunks in a single API call
    try:
        embeddings = await embeddings_service.embed_documents(chunks)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}"
        )

    # 5. Save Document and associated Memory chunks inside a transaction
    try:
        db_doc = Document(project_id=project_id, filename=filename)
        db.add(db_doc)
        await db.commit()
        await db.refresh(db_doc)

        db_memories = []
        for text_chunk, vector in zip(chunks, embeddings):
            db_mem = Memory(
                project_id=project_id,
                document_id=db_doc.id,
                content=text_chunk,
                embedding=vector
            )
            db_memories.append(db_mem)
            
        db.add_all(db_memories)
        await db.commit()

        from app.services.memory_hooks import on_document_uploaded
        await on_document_uploaded(project_id, db_doc.id, db_doc.filename)
        return db_doc
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database write failed: {str(e)}"
        )

@router.delete("/projects/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: Document = Depends(get_document_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete document and all its associated semantic memories."""
    await db.delete(document)
    await db.commit()
    return
