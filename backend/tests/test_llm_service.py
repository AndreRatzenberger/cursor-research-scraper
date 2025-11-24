"""Tests for LLM service."""

from backend.services.llm_service import LLMService


def test_llm_initialization():
    """Test LLM service initialization."""
    service = LLMService()
    
    # Check availability
    is_available = service.is_available()
    print(f"✓ LLM service initialized (available: {is_available})")


def test_placeholder_fallback():
    """Test that service returns placeholders when LLM unavailable."""
    service = LLMService()
    
    # Force unavailability for testing
    service.available = False
    
    result = service.generate_summary(
        title="Test Paper",
        abstract="This is a test abstract about machine learning."
    )
    
    # Should return placeholders
    assert result['summary'] == '<summary>'
    assert result['keywords'] == ['<keywords>']
    assert result['key_contributions'] == '<key_contributions>'
    
    print("✓ Placeholder fallback working correctly")


if __name__ == "__main__":
    test_llm_initialization()
    test_placeholder_fallback()
    print("\n✅ All LLM tests passed!")
