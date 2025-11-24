"""Embedding generation service with fallback support."""

import logging
import os
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings with automatic fallback."""
    
    def __init__(self):
        self.provider = None
        self.model_name = None
        self._initialize()
    
    def _initialize(self):
        """Initialize embedding provider with fallback."""
        # Try litellm first
        try:
            import litellm
            self.model_name = os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")
            self.provider = "litellm"
            logger.info(f"Using litellm for embeddings with model: {self.model_name}")
        except Exception as e:
            logger.warning(f"litellm embedding initialization failed: {e}")
            self._fallback_to_sentence_transformers()
    
    def _fallback_to_sentence_transformers(self):
        """Fallback to sentence-transformers."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.provider = "sentence-transformers"
            self.model_name = "all-MiniLM-L6-v2"
            logger.info("Fell back to sentence-transformers for embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize sentence-transformers: {e}")
            self.provider = None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self.provider:
            logger.error("No embedding provider available")
            return None
        
        try:
            if self.provider == "litellm":
                import litellm
                response = litellm.embedding(
                    model=self.model_name,
                    input=[text]
                )
                embedding = response.data[0]['embedding']
                logger.debug(f"Generated embedding using litellm (dim: {len(embedding)})")
                return embedding
            
            elif self.provider == "sentence-transformers":
                embedding = self.model.encode(text, convert_to_numpy=True)
                embedding_list = embedding.tolist()
                logger.debug(f"Generated embedding using sentence-transformers (dim: {len(embedding_list)})")
                return embedding_list
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            
            # Try fallback if litellm failed
            if self.provider == "litellm":
                logger.info("Attempting fallback to sentence-transformers")
                self._fallback_to_sentence_transformers()
                return self.generate_embedding(text)
            
            return None
    
    def compute_similarity(self, embedding1: List[float], 
                          embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    def is_available(self) -> bool:
        """Check if embedding service is available."""
        return self.provider is not None
