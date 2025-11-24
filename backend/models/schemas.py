"""Data schemas for papers, tasks, and relationships."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Paper(BaseModel):
    """Schema for a research paper."""
    
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    published: str  # ISO format date
    categories: List[str]
    pdf_url: str
    
    # LLM-generated fields (may be placeholders)
    summary: str = "<summary>"  # AI-generated summary
    keywords: List[str] = Field(default_factory=lambda: ["<keywords>"])
    key_contributions: str = "<key_contributions>"
    methodology: str = "<methodology>"
    results: str = "<results>"
    future_research: str = "<future_research>"
    
    # Full text extraction
    full_text: Optional[str] = None
    
    # User metadata
    status: str = "new"  # new, read, starred
    notes: str = ""
    user_tags: List[str] = Field(default_factory=list)
    
    # System metadata
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Embedding reference
    has_embedding: bool = False
    needs_backfill: bool = False  # True if LLM fields need backfilling


class PaperUpdate(BaseModel):
    """Schema for updating a paper."""
    
    status: Optional[str] = None
    notes: Optional[str] = None
    user_tags: Optional[List[str]] = None


class ContinuousImportTask(BaseModel):
    """Schema for a continuous import task."""
    
    task_id: str
    name: str
    category: Optional[str] = None  # arXiv category filter
    semantic_query: Optional[str] = None  # Semantic abstract matching
    text_query: Optional[str] = None  # Text search in title/abstract
    check_interval: int = 300  # seconds between checks
    is_active: bool = True
    
    # Statistics
    papers_imported: int = 0
    last_check: Optional[str] = None
    last_paper_found: Optional[str] = None
    
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Relationship(BaseModel):
    """Schema for paper relationships in the knowledge graph."""
    
    source_id: str  # arxiv_id
    target_id: str  # arxiv_id
    relationship_type: str  # "citation", "shared_author", "topic_similarity", "methodology_similarity"
    strength: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SearchQuery(BaseModel):
    """Schema for search requests."""
    
    query: str
    limit: int = 10


class TheoryQuery(BaseModel):
    """Schema for theory mode queries."""
    
    hypothesis: str
    limit: int = 5  # Number of pro/contra papers each


class TheoryResult(BaseModel):
    """Schema for theory mode results."""
    
    paper_id: str
    title: str
    authors: List[str]
    relevance_score: float
    argument_summary: str
    key_quotes: List[str] = Field(default_factory=list)
    stance: str  # "pro" or "contra"
