"""Database layer using TinyDB."""

import os
import logging
from typing import List, Optional, Dict, Any
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

from .schemas import Paper, ContinuousImportTask, Relationship

logger = logging.getLogger(__name__)


class Database:
    """Manages database operations for papers, tasks, and relationships."""
    
    def __init__(self, db_path: str = "./data/papertrail.json"):
        """Initialize database connection."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = TinyDB(db_path, storage=CachingMiddleware(JSONStorage))
        
        # Tables
        self.papers = self.db.table("papers")
        self.embeddings = self.db.table("embeddings")
        self.tasks = self.db.table("import_tasks")
        self.relationships = self.db.table("relationships")
        
        logger.info(f"Database initialized at {db_path}")
    
    # Paper operations
    def add_paper(self, paper: Paper) -> bool:
        """Add a paper to the database."""
        try:
            query = Query()
            existing = self.papers.get(query.arxiv_id == paper.arxiv_id)
            if existing:
                logger.debug(f"Paper {paper.arxiv_id} already exists, skipping")
                return False
            
            self.papers.insert(paper.model_dump())
            logger.info(f"Added paper: {paper.arxiv_id} - {paper.title}")
            return True
        except Exception as e:
            logger.error(f"Error adding paper {paper.arxiv_id}: {e}")
            return False
    
    def get_paper(self, arxiv_id: str) -> Optional[Paper]:
        """Get a paper by arXiv ID."""
        query = Query()
        result = self.papers.get(query.arxiv_id == arxiv_id)
        if result:
            return Paper(**result)
        return None
    
    def get_all_papers(self, skip: int = 0, limit: int = 100, 
                       status: Optional[str] = None) -> List[Paper]:
        """Get all papers with optional filtering."""
        query = Query()
        
        if status:
            results = self.papers.search(query.status == status)
        else:
            results = self.papers.all()
        
        # Apply pagination
        results = results[skip:skip + limit]
        return [Paper(**r) for r in results]
    
    def update_paper(self, arxiv_id: str, updates: Dict[str, Any]) -> bool:
        """Update a paper."""
        try:
            query = Query()
            from datetime import datetime
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            self.papers.update(updates, query.arxiv_id == arxiv_id)
            logger.info(f"Updated paper: {arxiv_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating paper {arxiv_id}: {e}")
            return False
    
    def get_papers_needing_backfill(self, limit: int = 10) -> List[Paper]:
        """Get papers that need LLM backfilling."""
        query = Query()
        results = self.papers.search(query.needs_backfill == True)[:limit]
        return [Paper(**r) for r in results]
    
    def count_papers(self) -> int:
        """Get total paper count."""
        return len(self.papers)
    
    # Embedding operations
    def store_embedding(self, arxiv_id: str, embedding: List[float]) -> bool:
        """Store embedding vector for a paper."""
        try:
            query = Query()
            existing = self.embeddings.get(query.arxiv_id == arxiv_id)
            
            if existing:
                self.embeddings.update(
                    {"embedding": embedding},
                    query.arxiv_id == arxiv_id
                )
            else:
                self.embeddings.insert({
                    "arxiv_id": arxiv_id,
                    "embedding": embedding
                })
            
            # Mark paper as having embedding
            self.update_paper(arxiv_id, {"has_embedding": True})
            logger.debug(f"Stored embedding for {arxiv_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing embedding for {arxiv_id}: {e}")
            return False
    
    def get_embedding(self, arxiv_id: str) -> Optional[List[float]]:
        """Get embedding for a paper."""
        query = Query()
        result = self.embeddings.get(query.arxiv_id == arxiv_id)
        if result:
            return result["embedding"]
        return None
    
    def get_all_embeddings(self) -> List[Dict[str, Any]]:
        """Get all embeddings."""
        return self.embeddings.all()
    
    # Task operations
    def add_task(self, task: ContinuousImportTask) -> bool:
        """Add a continuous import task."""
        try:
            query = Query()
            existing = self.tasks.get(query.task_id == task.task_id)
            if existing:
                return False
            
            self.tasks.insert(task.model_dump())
            logger.info(f"Added import task: {task.task_id} - {task.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding task {task.task_id}: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[ContinuousImportTask]:
        """Get a task by ID."""
        query = Query()
        result = self.tasks.get(query.task_id == task_id)
        if result:
            return ContinuousImportTask(**result)
        return None
    
    def get_all_tasks(self) -> List[ContinuousImportTask]:
        """Get all import tasks."""
        results = self.tasks.all()
        return [ContinuousImportTask(**r) for r in results]
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task."""
        try:
            query = Query()
            self.tasks.update(updates, query.task_id == task_id)
            logger.debug(f"Updated task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            query = Query()
            self.tasks.remove(query.task_id == task_id)
            logger.info(f"Deleted task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False
    
    # Relationship operations
    def add_relationship(self, relationship: Relationship) -> bool:
        """Add a relationship between papers."""
        try:
            query = Query()
            # Check if relationship already exists
            existing = self.relationships.get(
                (query.source_id == relationship.source_id) & 
                (query.target_id == relationship.target_id) &
                (query.relationship_type == relationship.relationship_type)
            )
            if existing:
                return False
            
            self.relationships.insert(relationship.model_dump())
            logger.debug(f"Added relationship: {relationship.source_id} -> {relationship.target_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            return False
    
    def get_relationships(self, arxiv_id: str) -> List[Relationship]:
        """Get all relationships for a paper."""
        query = Query()
        results = self.relationships.search(
            (query.source_id == arxiv_id) | (query.target_id == arxiv_id)
        )
        return [Relationship(**r) for r in results]
    
    def close(self):
        """Close database connection."""
        self.db.close()
        logger.info("Database connection closed")
