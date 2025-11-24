"""Continuous import worker for fetching papers from arXiv."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Callable

from backend.models.database import Database
from backend.models.schemas import ContinuousImportTask
from backend.services.arxiv_service import ArxivService
from backend.services.embedding_service import EmbeddingService
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ContinuousImportWorker:
    """Worker for continuous paper import from arXiv."""
    
    def __init__(self, db: Database, arxiv_service: ArxivService,
                 embedding_service: EmbeddingService, llm_service: LLMService,
                 progress_callback: Optional[Callable] = None):
        self.db = db
        self.arxiv_service = arxiv_service
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.progress_callback = progress_callback
        
        self.running_tasks: Dict[str, asyncio.Task] = {}
    
    async def start_task(self, task: ContinuousImportTask):
        """Start a continuous import task."""
        if task.task_id in self.running_tasks:
            logger.warning(f"Task {task.task_id} already running")
            return
        
        # Create async task
        async_task = asyncio.create_task(self._run_import_loop(task))
        self.running_tasks[task.task_id] = async_task
        
        logger.info(f"Started continuous import task: {task.task_id} - {task.name}")
    
    async def stop_task(self, task_id: str):
        """Stop a continuous import task."""
        if task_id not in self.running_tasks:
            logger.warning(f"Task {task_id} not running")
            return
        
        # Cancel the task
        self.running_tasks[task_id].cancel()
        try:
            await self.running_tasks[task_id]
        except asyncio.CancelledError:
            pass
        
        del self.running_tasks[task_id]
        
        # Update task status
        self.db.update_task(task_id, {"is_active": False})
        
        logger.info(f"Stopped continuous import task: {task_id}")
    
    async def _run_import_loop(self, task: ContinuousImportTask):
        """Main loop for continuous import."""
        while True:
            try:
                logger.info(f"Running import check for task: {task.task_id}")
                
                # Fetch papers based on task configuration
                papers = []
                
                if task.category:
                    papers = self.arxiv_service.fetch_latest_papers(
                        category=task.category,
                        max_results=10
                    )
                elif task.text_query:
                    papers = self.arxiv_service.search_papers(
                        query=task.text_query,
                        max_results=10
                    )
                else:
                    papers = self.arxiv_service.fetch_latest_papers(max_results=10)
                
                # Process papers
                new_papers_count = 0
                for paper in papers:
                    # Check if already exists
                    existing = self.db.get_paper(paper.arxiv_id)
                    if existing:
                        continue
                    
                    # Generate embedding
                    if self.embedding_service.is_available():
                        embedding_text = f"{paper.title} {paper.abstract}"
                        embedding = self.embedding_service.generate_embedding(embedding_text)
                        if embedding:
                            self.db.store_embedding(paper.arxiv_id, embedding)
                    
                    # Generate summary if LLM available
                    if self.llm_service.is_available():
                        summary_data = self.llm_service.generate_summary(
                            paper.title,
                            paper.abstract
                        )
                        paper.summary = summary_data.get('summary', '<summary>')
                        paper.keywords = summary_data.get('keywords', ['<keywords>'])
                        paper.key_contributions = summary_data.get('key_contributions', '<key_contributions>')
                        paper.methodology = summary_data.get('methodology', '<methodology>')
                        paper.results = summary_data.get('results', '<results>')
                        paper.future_research = summary_data.get('future_research', '<future_research>')
                        paper.needs_backfill = False
                    
                    # Add to database
                    if self.db.add_paper(paper):
                        new_papers_count += 1
                        
                        # Send progress update
                        if self.progress_callback:
                            await self.progress_callback({
                                'type': 'paper_imported',
                                'task_id': task.task_id,
                                'paper': {
                                    'arxiv_id': paper.arxiv_id,
                                    'title': paper.title
                                }
                            })
                
                # Update task statistics
                self.db.update_task(task.task_id, {
                    'papers_imported': task.papers_imported + new_papers_count,
                    'last_check': datetime.utcnow().isoformat(),
                    'last_paper_found': datetime.utcnow().isoformat() if new_papers_count > 0 else task.last_paper_found
                })
                
                logger.info(f"Task {task.task_id}: imported {new_papers_count} new papers")
                
                # Wait for next check
                await asyncio.sleep(task.check_interval)
                
                # Reload task to get updated configuration
                task = self.db.get_task(task.task_id)
                if not task or not task.is_active:
                    break
                
            except asyncio.CancelledError:
                logger.info(f"Task {task.task_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in import loop for task {task.task_id}: {e}")
                # Wait before retrying
                await asyncio.sleep(60)
    
    def get_running_tasks(self) -> list:
        """Get list of running task IDs."""
        return list(self.running_tasks.keys())
    
    async def stop_all(self):
        """Stop all running tasks."""
        task_ids = list(self.running_tasks.keys())
        for task_id in task_ids:
            await self.stop_task(task_id)
