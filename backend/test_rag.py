# backend/test_rag.py
import asyncio
import os
import sys
from sqlalchemy import select

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import AsyncSessionLocal, sync_engine
from app.db.models import Base, Project, Document, Memory
from app.services.embeddings import similarity_search, embeddings_service
from app.api.routes.documents import RecursiveCharacterTextSplitter

async def test_rag_flow():
    print("Starting RAG Vector Search & Chunking Test...")
    print("---------------------------------------------")
    
    # 1. Initialize Tables
    print("Initializing Database tables...")
    Base.metadata.create_all(bind=sync_engine)
    
    # 2. Setup Async Session
    async with AsyncSessionLocal() as db:
        # 3. Create a test Project
        print("Creating mock project...")
        test_project = Project(
            name="RAG Test Startup",
            core_context={
                "value_proposition": "An AI platform for veterinary diagnostics.",
                "target_audience": "Veterinary clinics",
                "tech_stack": "FastAPI, Next.js, PyTorch",
                "business_model": "SaaS per diagnostic run"
            },
            user_id="test_user_placeholder"  # Just a placeholder since Clerk is not running here
        )
        db.add(test_project)
        await db.commit()
        await db.refresh(test_project)
        project_id = test_project.id
        print(f"Mock Project created with ID: {project_id}")

        try:
            # 4. Mock Document content
            filename = "quantum_secret_sauce.txt"
            raw_text = (
                "Project Mercury secret sauce: our proprietary algorithm uses quantum-inspired annealing "
                "running on simulated hardware to optimize delivery routes. By mapping logistics to a spin-glass Hamiltonian, "
                "we reduce calculation latency from 45 minutes to 1.2 seconds. "
                "The core engineering team consists of 3 ex-Google Quantum scientists who joined in 2025."
            )
            
            print(f"Uploading mock text file: {filename}...")
            # 5. Split text
            splitter = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=20)
            chunks = splitter.split_text(raw_text)
            print(f"Split raw text into {len(chunks)} chunks:")
            for i, chunk in enumerate(chunks):
                print(f"  Chunk [{i}]: {chunk!r}")
            
            # 6. Generate embeddings
            print("Generating Gemini embeddings (text-embedding-004)...")
            embeddings = await embeddings_service.embed_documents(chunks)
            print(f"Successfully generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")
            
            # 7. Persist Document & Memories
            print("Persisting Document and Memory chunks in Database...")
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
            print("Successfully saved vector chunks to Database.")
            
            # 8. Perform similarity search queries
            test_queries = [
                "How does the route optimization algorithm work?",
                "Who are the founders or engineers?"
            ]
            
            for query in test_queries:
                print(f"\nRunning similarity search for query: {query!r}...")
                results = await similarity_search(db, project_id, query, limit=2)
                print(f"Found {len(results)} matches:")
                for r in results:
                    print(f"  - Match: {r.content!r}")
                
                assert len(results) > 0, "No search results returned!"
                
            # 9. Verify Cascade Deletion
            print(f"\nTesting Document deletion with cascade on Document ID: {db_doc.id}...")
            await db.delete(db_doc)
            await db.commit()
            
            # Query memories to check if they are deleted
            result = await db.execute(select(Memory).where(Memory.document_id == db_doc.id))
            remaining_memories = result.scalars().all()
            print(f"Associated memories remaining after deletion: {len(remaining_memories)}")
            assert len(remaining_memories) == 0, "Memory chunks were NOT cascade-deleted!"
            print("Cascade deletion verified successfully.")

        finally:
            # Cleanup mock project
            print("\nCleaning up mock project...")
            await db.delete(test_project)
            await db.commit()
            print("Cleanup completed.")

if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is present
    if not os.environ.get("GEMINI_API_KEY") and not settings.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable is not set!")
        sys.exit(1)
        
    asyncio.run(test_rag_flow())
