"""Test runner - runs all backend tests."""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# Import test modules
import backend.tests.test_database as test_database
import backend.tests.test_embedding_service as test_embedding_service
import backend.tests.test_llm_service as test_llm_service


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running PaperTrail Backend Tests")
    print("=" * 60)
    print()
    
    try:
        # Database tests
        print("Testing Database Layer...")
        print("-" * 60)
        test_database.test_paper_operations()
        test_database.test_embedding_operations()
        test_database.test_task_operations()
        test_database.test_relationship_operations()
        print()
        
        # Embedding service tests
        print("Testing Embedding Service...")
        print("-" * 60)
        test_embedding_service.test_embedding_initialization()
        test_embedding_service.test_embedding_generation()
        test_embedding_service.test_similarity_computation()
        print()
        
        # LLM service tests
        print("Testing LLM Service...")
        print("-" * 60)
        test_llm_service.test_llm_initialization()
        test_llm_service.test_placeholder_fallback()
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
