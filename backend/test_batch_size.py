# backend/test_batch_size.py
import inspect
from langchain_google_genai import GoogleGenerativeAIEmbeddings

try:
    print(inspect.getsource(GoogleGenerativeAIEmbeddings._prepare_batches))
except Exception as e:
    print(e)
