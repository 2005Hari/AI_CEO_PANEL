# backend/test_new_sdk.py
import os
import sys
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
texts = ["hello", "world", "test", "another one"]

config = types.EmbedContentConfig(
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=768
)

try:
    result = client.models.embed_content(
        model="models/gemini-embedding-2",
        contents=texts,
        config=config,
    )
    print("Result attributes:", dir(result))
    print("Result.embeddings:", result.embeddings)
    if result.embeddings:
        print("Type of result.embeddings:", type(result.embeddings))
        print("Length of result.embeddings:", len(result.embeddings))
        print("First element attributes:", dir(result.embeddings[0]))
        # Check if values exists
        print("First element values:", result.embeddings[0].values)
except Exception as e:
    print("Error:", e)
