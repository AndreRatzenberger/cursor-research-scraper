"""Main FastAPI application for PaperTrail backend."""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.models.database import Database
from backend.models.schemas import (
    Paper, PaperUpdate, ContinuousImportTask, SearchQuery, 
    TheoryQuery, TheoryResult
)
from backend.services.arxiv_service import ArxivService
from backend.services.embedding_service import EmbeddingService
from backend.services.llm_service import LLMService
from backend.services.graph_service import GraphService
from backend.workers.continuous_import import ContinuousImportWorker
from backend.workers.backfill_worker import BackfillWorker

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
db: Database = None
arxiv_service: ArxivService = None
embedding_service: EmbeddingService = None
llm_service: LLMService = None
graph_service: GraphService = None
import_worker: ContinuousImportWorker = None
backfill_worker: BackfillWorker = None

# WebSocket connections
websocket_connections: List[WebSocket] = []


async def broadcast_message(message: dict):
    """Broadcast message to all WebSocket connections."""
    for connection in websocket_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    global db, arxiv_service, embedding_service, llm_service, graph_service, import_worker, backfill_worker
    
    logger.info("Starting PaperTrail backend...")
    
    # Initialize services
    db_path = os.getenv("DB_PATH", "./data/papertrail.json")
    db = Database(db_path)
    arxiv_service = ArxivService()
    embedding_service = EmbeddingService()
    llm_service = LLMService()
    graph_service = GraphService(db, embedding_service)
    
    # Build knowledge graph
    graph_service.build_graph()
    
    # Initialize workers
    import_worker = ContinuousImportWorker(
        db, arxiv_service, embedding_service, llm_service,
        progress_callback=broadcast_message
    )
    backfill_worker = BackfillWorker(
        db, llm_service,
        progress_callback=broadcast_message
    )
    
    # Start backfill worker
    await backfill_worker.start()
    
    # Resume active import tasks
    tasks = db.get_all_tasks()
    for task in tasks:
        if task.is_active:
            await import_worker.start_task(task)
    
    logger.info("Backend startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PaperTrail backend...")
    
    # Stop workers
    await import_worker.stop_all()
    await backfill_worker.stop()
    
    # Close database
    db.close()
    
    logger.info("Backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="PaperTrail API",
    description="Research paper catalog with GraphRAG",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "llm_available": llm_service.is_available(),
        "embedding_available": embedding_service.is_available()
    }


# Paper endpoints
@app.post("/api/papers/ingest")
async def ingest_paper(arxiv_url: str):
    """Ingest a paper from arXiv URL."""
    logger.info(f"Ingesting paper from URL: {arxiv_url}")
    
    try:
        # Extract arXiv ID from URL
        arxiv_id = arxiv_url.split('/')[-1].split('v')[0]
        
        # Check if already exists
        existing = db.get_paper(arxiv_id)
        if existing:
            raise HTTPException(status_code=400, detail="Paper already exists")
        
        # Fetch paper
        paper = arxiv_service.fetch_paper(arxiv_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found on arXiv")
        
        # Generate embedding
        if embedding_service.is_available():
            embedding_text = f"{paper.title} {paper.abstract}"
            embedding = embedding_service.generate_embedding(embedding_text)
            if embedding:
                db.store_embedding(paper.arxiv_id, embedding)
        
        # Generate summary if LLM available
        if llm_service.is_available():
            summary_data = llm_service.generate_summary(paper.title, paper.abstract)
            paper.summary = summary_data.get('summary', '<summary>')
            paper.keywords = summary_data.get('keywords', ['<keywords>'])
            paper.key_contributions = summary_data.get('key_contributions', '<key_contributions>')
            paper.methodology = summary_data.get('methodology', '<methodology>')
            paper.results = summary_data.get('results', '<results>')
            paper.future_research = summary_data.get('future_research', '<future_research>')
            paper.needs_backfill = False
        
        # Add to database
        db.add_paper(paper)
        
        # Discover relationships
        all_papers = db.get_all_papers(limit=1000)
        relationships = graph_service.discover_relationships(paper, all_papers)
        for rel in relationships:
            db.add_relationship(rel)
        
        # Rebuild graph
        graph_service.build_graph()
        
        # Broadcast update
        await broadcast_message({
            'type': 'paper_ingested',
            'paper': {
                'arxiv_id': paper.arxiv_id,
                'title': paper.title
            }
        })
        
        logger.info(f"Successfully ingested paper: {paper.arxiv_id}")
        return paper
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers", response_model=List[Paper])
async def list_papers(skip: int = 0, limit: int = 100, status: Optional[str] = None):
    """List all papers."""
    logger.debug(f"Listing papers: skip={skip}, limit={limit}, status={status}")
    papers = db.get_all_papers(skip=skip, limit=limit, status=status)
    return papers


@app.get("/api/papers/{arxiv_id}", response_model=Paper)
async def get_paper(arxiv_id: str):
    """Get a specific paper."""
    logger.debug(f"Getting paper: {arxiv_id}")
    paper = db.get_paper(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@app.patch("/api/papers/{arxiv_id}")
async def update_paper(arxiv_id: str, updates: PaperUpdate):
    """Update a paper."""
    logger.info(f"Updating paper: {arxiv_id}")
    
    paper = db.get_paper(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    update_dict = updates.model_dump(exclude_none=True)
    db.update_paper(arxiv_id, update_dict)
    
    return {"success": True}


@app.get("/api/papers/{arxiv_id}/similar")
async def get_similar_papers(arxiv_id: str, limit: int = 5):
    """Get similar papers."""
    logger.debug(f"Finding similar papers for: {arxiv_id}")
    
    paper = db.get_paper(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    similar = graph_service.find_similar_papers(arxiv_id, limit=limit)
    return similar


@app.get("/api/papers/{arxiv_id}/relationships")
async def get_paper_relationships(arxiv_id: str):
    """Get paper relationships for graph visualization."""
    logger.debug(f"Getting relationships for: {arxiv_id}")
    
    paper = db.get_paper(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    connections = graph_service.get_paper_connections(arxiv_id)
    return connections


# Search endpoints
@app.post("/api/search")
async def search_papers(query: SearchQuery):
    """Search papers using vector similarity."""
    logger.info(f"Searching papers: {query.query}")
    
    if not embedding_service.is_available():
        raise HTTPException(status_code=503, detail="Embedding service unavailable")
    
    try:
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(query.query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Get all embeddings and compute similarities
        all_embeddings = db.get_all_embeddings()
        
        results = []
        for emb_data in all_embeddings:
            similarity = embedding_service.compute_similarity(
                query_embedding,
                emb_data['embedding']
            )
            results.append({
                'arxiv_id': emb_data['arxiv_id'],
                'similarity': similarity
            })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:query.limit]
        
        # Get paper details
        papers = []
        for result in results:
            paper = db.get_paper(result['arxiv_id'])
            if paper:
                papers.append({
                    **paper.model_dump(),
                    'similarity': result['similarity']
                })
        
        logger.info(f"Found {len(papers)} papers for query")
        return papers
        
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Theory mode endpoints
@app.post("/api/theory", response_model=dict)
async def analyze_theory(query: TheoryQuery):
    """Analyze papers for pro/contra arguments on a hypothesis."""
    logger.info(f"Analyzing theory: {query.hypothesis}")
    
    if not llm_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Theory mode requires LLM service, which is currently unavailable"
        )
    
    try:
        # Get relevant papers (using semantic search)
        if not embedding_service.is_available():
            raise HTTPException(status_code=503, detail="Embedding service unavailable")
        
        query_embedding = embedding_service.generate_embedding(query.hypothesis)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Get top papers by similarity
        all_embeddings = db.get_all_embeddings()
        similarities = []
        for emb_data in all_embeddings:
            similarity = embedding_service.compute_similarity(
                query_embedding,
                emb_data['embedding']
            )
            similarities.append({
                'arxiv_id': emb_data['arxiv_id'],
                'similarity': similarity
            })
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        similarities = similarities[:query.limit * 2]  # Get more papers than needed
        
        # Get paper details
        papers = []
        for sim in similarities:
            paper = db.get_paper(sim['arxiv_id'])
            if paper:
                papers.append(paper.model_dump())
        
        # Analyze papers
        results = llm_service.analyze_theory(query.hypothesis, papers)
        
        # Separate pro and contra
        pro_results = [r for r in results if r['stance'] == 'pro']
        contra_results = [r for r in results if r['stance'] == 'contra']
        
        # Sort by relevance
        pro_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        contra_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Limit results
        pro_results = pro_results[:query.limit]
        contra_results = contra_results[:query.limit]
        
        logger.info(f"Theory analysis complete: {len(pro_results)} pro, {len(contra_results)} contra")
        
        return {
            'hypothesis': query.hypothesis,
            'pro_arguments': pro_results,
            'contra_arguments': contra_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing theory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Continuous import task endpoints
@app.post("/api/tasks")
async def create_import_task(task: ContinuousImportTask):
    """Create a continuous import task."""
    logger.info(f"Creating import task: {task.name}")
    
    if not db.add_task(task):
        raise HTTPException(status_code=400, detail="Task already exists")
    
    if task.is_active:
        await import_worker.start_task(task)
    
    return task


@app.get("/api/tasks", response_model=List[ContinuousImportTask])
async def list_tasks():
    """List all import tasks."""
    logger.debug("Listing import tasks")
    return db.get_all_tasks()


@app.get("/api/tasks/{task_id}", response_model=ContinuousImportTask)
async def get_task(task_id: str):
    """Get a specific task."""
    logger.debug(f"Getting task: {task_id}")
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/tasks/{task_id}/start")
async def start_task(task_id: str):
    """Start a task."""
    logger.info(f"Starting task: {task_id}")
    
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.update_task(task_id, {"is_active": True})
    task.is_active = True
    
    await import_worker.start_task(task)
    return {"success": True}


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a task."""
    logger.info(f"Stopping task: {task_id}")
    
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await import_worker.stop_task(task_id)
    return {"success": True}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    logger.info(f"Deleting task: {task_id}")
    
    # Stop if running
    if task_id in import_worker.get_running_tasks():
        await import_worker.stop_task(task_id)
    
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"success": True}


# Dashboard endpoints
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics."""
    logger.debug("Getting dashboard statistics")
    
    papers = db.get_all_papers(limit=10000)
    
    # Count papers by category
    category_counts = {}
    for paper in papers:
        for cat in paper.categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Count papers by status
    status_counts = {}
    for paper in papers:
        status_counts[paper.status] = status_counts.get(paper.status, 0) + 1
    
    # Get active tasks
    tasks = db.get_all_tasks()
    active_tasks = [t for t in tasks if t.is_active]
    
    # Graph statistics
    graph_stats = graph_service.get_statistics()
    
    return {
        'total_papers': len(papers),
        'papers_by_category': category_counts,
        'papers_by_status': status_counts,
        'active_import_tasks': len(active_tasks),
        'total_import_tasks': len(tasks),
        'graph_stats': graph_stats,
        'llm_available': llm_service.is_available(),
        'embedding_available': embedding_service.is_available()
    }


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
        websocket_connections.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
