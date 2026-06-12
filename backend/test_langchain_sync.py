# backend/test_langchain_sync.py
import os
import sys
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2",
    output_dimensionality=768,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
texts = ["hello", "world", "test", "another one"]

sync_res = embeddings.embed_documents(texts)
print("Sync Length:", len(sync_res))

async def check_async():
    async_res = await embeddings.aembed_documents(texts)
    print("Async Length:", len(async_res))

asyncio.run(check_async())
