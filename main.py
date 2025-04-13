# main.py (Meticulously Refined with PDF Error Handling)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import PyPDF2
from PyPDF2.errors import PdfReadError
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
import requests
import os

app = FastAPI()

# Enable CORS for Electron frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
collection_name = "pdf_chunks"
qdrant_path = "./local_qdrant"

# Initialize Qdrant client
client = QdrantClient(path=qdrant_path)

# Ensure collection exists (based on embedding dimension for MiniLM)
if collection_name not in [col.name for col in client.get_collections().collections]:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

# Load lightweight embedding model (50MB)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-MiniLM-L3-v2")

# Create vector store wrapper
vector_store = QdrantVectorStore(
    client=client,
    collection_name=collection_name,
    embedding=embedding_model,
)

# Endpoint: Upload and store PDF chunks 
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    try:
        reader = PyPDF2.PdfReader(file.file)
        text = "\n".join([page.extract_text() or '' for page in reader.pages])
    except PdfReadError:
        raise HTTPException(status_code=400, detail="Invalid PDF format or EOF marker not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error while reading PDF: {e}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=384, chunk_overlap=50)
    chunks = splitter.create_documents([text])

    vector_store.add_documents(chunks)
    return {"message": "PDF processed and stored", "chunks": len(chunks)}

# Endpoint: Query PDF content using TinyLLaMA
@app.post("/query/")
async def query(query: str = Form(...)):
    retriever = vector_store.as_retriever()
    docs = retriever.get_relevant_documents(query)

    context = "\n".join([doc.page_content for doc in docs])
    prompt = f"Answer the following question using the given context.\n\nContext:\n{context}\n\nQuestion: {query}"

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "tinyllama", "prompt": prompt, "stream": False}
        )
        result = res.json().get("response", "No response returned from LLM.")
    except Exception as e:
        result = f"LLM call failed: {e}"

    return {"answer": result}
