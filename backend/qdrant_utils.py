# backend/qdrant_utils.py
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)
collection_name = "documents"

# Recreate collection (delete if exists, then create)
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

def insert_vectors(vector, payload):
    client.upsert(
        collection_name=collection_name,
        points=[{
            "id": str(uuid.uuid4()),  # <-- generate a unique string ID
            "vector": vector,
            "payload": payload
        }]
    )

def search_vectors(vector, top=3, threshold=0.4):
    results = client.search(
        collection_name=collection_name,
        query_vector=vector,
        limit=top
    )
    # Only keep results above similarity threshold
    return [res for res in results if res.score >= threshold]
