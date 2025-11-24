"""Tests for database layer."""

import os
import tempfile
from backend.models.database import Database
from backend.models.schemas import Paper, ContinuousImportTask, Relationship


def test_paper_operations():
    """Test adding, retrieving, and updating papers."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Test adding paper
        paper = Paper(
            arxiv_id="2103.00020",
            title="Test Paper",
            authors=["Author One", "Author Two"],
            abstract="This is a test abstract.",
            published="2021-03-01T00:00:00",
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2103.00020.pdf"
        )
        
        assert db.add_paper(paper) is True
        
        # Test duplicate detection
        assert db.add_paper(paper) is False
        
        # Test retrieval
        retrieved = db.get_paper("2103.00020")
        assert retrieved is not None
        assert retrieved.title == "Test Paper"
        
        # Test update
        db.update_paper("2103.00020", {"status": "read"})
        updated = db.get_paper("2103.00020")
        assert updated.status == "read"
        
        # Test listing
        papers = db.get_all_papers()
        assert len(papers) == 1
        
        db.close()
        print("✓ Paper operations test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_embedding_operations():
    """Test storing and retrieving embeddings."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Add paper first
        paper = Paper(
            arxiv_id="2103.00020",
            title="Test Paper",
            authors=["Author One"],
            abstract="Abstract",
            published="2021-03-01T00:00:00",
            categories=["cs.AI"],
            pdf_url="https://test.pdf"
        )
        db.add_paper(paper)
        
        # Test storing embedding
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        assert db.store_embedding("2103.00020", embedding) is True
        
        # Test retrieval
        retrieved = db.get_embedding("2103.00020")
        assert retrieved == embedding
        
        # Verify paper was updated
        paper = db.get_paper("2103.00020")
        assert paper.has_embedding is True
        
        db.close()
        print("✓ Embedding operations test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_task_operations():
    """Test import task management."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Test adding task
        task = ContinuousImportTask(
            task_id="test-task-1",
            name="Test Import Task",
            category="cs.AI",
            check_interval=300,
            is_active=True
        )
        
        assert db.add_task(task) is True
        
        # Test duplicate detection
        assert db.add_task(task) is False
        
        # Test retrieval
        retrieved = db.get_task("test-task-1")
        assert retrieved is not None
        assert retrieved.name == "Test Import Task"
        
        # Test update
        db.update_task("test-task-1", {"papers_imported": 5})
        updated = db.get_task("test-task-1")
        assert updated.papers_imported == 5
        
        # Test listing
        tasks = db.get_all_tasks()
        assert len(tasks) == 1
        
        # Test deletion
        assert db.delete_task("test-task-1") is True
        assert db.get_task("test-task-1") is None
        
        db.close()
        print("✓ Task operations test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_relationship_operations():
    """Test relationship management."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Test adding relationship
        rel = Relationship(
            source_id="2103.00020",
            target_id="2103.00021",
            relationship_type="citation",
            strength=0.8
        )
        
        assert db.add_relationship(rel) is True
        
        # Test duplicate detection
        assert db.add_relationship(rel) is False
        
        # Test retrieval
        relationships = db.get_relationships("2103.00020")
        assert len(relationships) == 1
        assert relationships[0].target_id == "2103.00021"
        
        db.close()
        print("✓ Relationship operations test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    test_paper_operations()
    test_embedding_operations()
    test_task_operations()
    test_relationship_operations()
    print("\n✅ All database tests passed!")
