import os
import json
import logging
import numpy as np
import faiss
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class CodeVectorStore:
    """
    Stores and retrieves code embeddings using FAISS.
    """
    
    def __init__(self, vector_dimension: int = 768):  # Changed from 1536 to 768 for CodeBERT
        self.vector_dimension = vector_dimension
        self.index = None
        self.metadata = []
        self.chunks = []
        self.index_path = os.path.join(os.getcwd(), "vector_store")
        os.makedirs(self.index_path, exist_ok=True)

    def add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """
        Add code embeddings and metadata to the store.
        """
        if not embeddings_data:
            logger.warning("No embeddings data provided.")
            return False

        try:
            vectors = np.array([item["embedding"] for item in embeddings_data], dtype=np.float32)

            if self.index is None:
                # Use IndexFlatIP because all embeddings are unit-normalized
                self.index = faiss.IndexFlatIP(self.vector_dimension)

            self.index.add(vectors)

            self.metadata.extend([item["metadata"] for item in embeddings_data])
            self.chunks.extend([item["chunk"] for item in embeddings_data])

            logger.info(f"Added {len(embeddings_data)} embeddings to vector store.")
            return True
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            return False

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the top_k most similar code chunks.
        """
        if self.index is None or not self.metadata:
            logger.warning("Vector store is empty.")
            return []

        try:
            query = np.array([query_embedding], dtype=np.float32)
            distances, indices = self.index.search(query, min(top_k, len(self.metadata)))

            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.metadata):
                    # Convert L2 distance to a similarity score (higher is better)
                    # For CodeBERT, we can use a simple normalization
                    distance = float(distances[0][i])
                    max_distance = float(self.vector_dimension)  # Theoretical max L2 distance for normalized vectors
                    similarity = 1.0 - (distance / max_distance)
                    
                    results.append({
                        "chunk": self.chunks[idx],
                        "metadata": self.metadata[idx],
                        "distance": distance,
                        "similarity": similarity
                    })
            
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def save(self, filename: str = "code_vector_store") -> bool:
        """
        Persist the vector store index and metadata to disk.
        """
        try:
            if self.index is None:
                logger.warning("No index to save.")
                return False
                
            faiss.write_index(self.index, os.path.join(self.index_path, f"{filename}.index"))

            with open(os.path.join(self.index_path, f"{filename}_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(self.metadata, f)

            with open(os.path.join(self.index_path, f"{filename}_chunks.json"), "w", encoding="utf-8") as f:
                json.dump(self.chunks, f)

            logger.info(f"Saved vector store to {self.index_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            return False

    def load(self, filename: str = "code_vector_store") -> bool:
        """
        Load the vector store from disk.
        """
        try:
            index_path = os.path.join(self.index_path, f"{filename}.index")
            meta_path = os.path.join(self.index_path, f"{filename}_metadata.json")
            chunks_path = os.path.join(self.index_path, f"{filename}_chunks.json")

            if not all(os.path.exists(p) for p in [index_path, meta_path, chunks_path]):
                logger.warning(f"Vector store files not found in {self.index_path}")
                return False

            self.index = faiss.read_index(index_path)
            self.vector_dimension = self.index.d  # Update dimension from loaded index

            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

            with open(chunks_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)

            logger.info(f"Loaded vector store from {self.index_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    def clear(self) -> bool:
        """
        Reset the vector store in memory.
        """
        try:
            self.index = None
            self.metadata.clear()
            self.chunks.clear()
            logger.info("Cleared vector store.")
            return True
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics of the vector store.
        """
        return {
            "total_embeddings": len(self.metadata),
            "vector_dimension": self.vector_dimension,
            "file_extensions": list({m.get("file_extension", "unknown") for m in self.metadata}),
            "total_files": len({m.get("file_path", "unknown") for m in self.metadata}),
            "total_tokens": sum(m.get("token_count", 0) for m in self.metadata)
        }


def create_vector_store() -> CodeVectorStore:
    return CodeVectorStore()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = create_vector_store()

    if store.load():
        logger.info(f"Loaded vector store with stats: {store.get_stats()}")
    else:
        logger.info("Vector store is empty or missing.")