# backend/embeddings.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # free and lightweight

def get_embedding(text):
    return model.encode(text).tolist()  # convert to list of floats

