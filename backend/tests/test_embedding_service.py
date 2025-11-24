"""Tests for embedding service."""

from backend.services.embedding_service import EmbeddingService


def test_embedding_initialization():
    """Test embedding service initialization."""
    service = EmbeddingService()
    
    # Should have a provider (either litellm or sentence-transformers)
    assert service.provider is not None
    assert service.provider in ["litellm", "sentence-transformers"]
    
    print(f"✓ Embedding service initialized with provider: {service.provider}")


def test_embedding_generation():
    """Test generating embeddings."""
    service = EmbeddingService()
    
    if not service.is_available():
        print("⚠ Embedding service not available, skipping test")
        return
    
    text = "This is a test paper about machine learning and neural networks."
    embedding = service.generate_embedding(text)
    
    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, (int, float)) for x in embedding)
    
    print(f"✓ Generated embedding with dimension: {len(embedding)}")


def test_similarity_computation():
    """Test cosine similarity computation."""
    service = EmbeddingService()
    
    # Create test embeddings
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [0.0, 1.0, 0.0]
    emb3 = [1.0, 0.0, 0.0]
    
    # Test similarity
    sim_different = service.compute_similarity(emb1, emb2)
    sim_same = service.compute_similarity(emb1, emb3)
    
    assert sim_different < sim_same
    assert 0.99 <= sim_same <= 1.01  # Should be very close to 1.0
    
    print(f"✓ Similarity computation working (same: {sim_same:.2f}, different: {sim_different:.2f})")


if __name__ == "__main__":
    test_embedding_initialization()
    test_embedding_generation()
    test_similarity_computation()
    print("\n✅ All embedding tests passed!")
