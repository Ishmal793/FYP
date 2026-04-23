import faiss
import numpy as np
import os

INDEX_FILE = "candidates.index"
DIMENSION = 384 # For all-MiniLM-L6-v2

def create_or_load_index():
    """Load FAISS index from disk or create a new one."""
    if os.path.exists(INDEX_FILE):
        return faiss.read_index(INDEX_FILE)
    else:
        # IndexFlatIP is used for inner product (cosine similarity on normalized vectors)
        # IndexFlatL2 is used for Euclidean distance
        index = faiss.IndexFlatL2(DIMENSION)
        return index

def save_index(index):
    """Persist index to disk."""
    faiss.write_index(index, INDEX_FILE)

def add_to_index(index, embedding, id_map):
    """Add a single embedding to the index."""
    vector = np.array([embedding]).astype('float32')
    index.add(vector)
    # The caller is responsible for mapping index position to DB ID
    return index.ntotal - 1

def search_index(index, query_embedding, k=20):
    """Search for top k similar vectors."""
    query_vector = np.array([query_embedding]).astype('float32')
    distances, indices = index.search(query_vector, k)
    return distances[0], indices[0]
