"""Backfill worker for processing papers with placeholder fields."""

import asyncio
import logging
from typing import Optional, Callable

from backend.models.database import Database
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class BackfillWorker:
    """Worker for backfilling LLM-generated fields when LLM becomes available."""
    
    def __init__(self, db: Database, llm_service: LLMService,
                 progress_callback: Optional[Callable] = None):
        self.db = db
        self.llm_service = llm_service
        self.progress_callback = progress_callback
        
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the backfill worker."""
        if self.running:
            logger.warning("Backfill worker already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_backfill_loop())
        logger.info("Started backfill worker")
    
    async def stop(self):
        """Stop the backfill worker."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped backfill worker")
    
    async def _run_backfill_loop(self):
        """Main loop for backfilling papers."""
        while self.running:
            try:
                # Check if LLM is available
                if not self.llm_service.is_available():
                    logger.debug("LLM not available, waiting...")
                    await asyncio.sleep(60)  # Check every minute
                    continue
                
                # Get papers needing backfill
                papers = self.db.get_papers_needing_backfill(limit=5)
                
                if not papers:
                    logger.debug("No papers need backfilling")
                    await asyncio.sleep(300)  # Check every 5 minutes if nothing to do
                    continue
                
                logger.info(f"Backfilling {len(papers)} papers...")
                
                for paper in papers:
                    try:
                        # Generate summary
                        summary_data = self.llm_service.generate_summary(
                            paper.title,
                            paper.abstract,
                            paper.full_text
                        )
                        
                        # Update paper
                        updates = {
                            'summary': summary_data.get('summary', '<summary>'),
                            'keywords': summary_data.get('keywords', ['<keywords>']),
                            'key_contributions': summary_data.get('key_contributions', '<key_contributions>'),
                            'methodology': summary_data.get('methodology', '<methodology>'),
                            'results': summary_data.get('results', '<results>'),
                            'future_research': summary_data.get('future_research', '<future_research>'),
                            'needs_backfill': False
                        }
                        
                        self.db.update_paper(paper.arxiv_id, updates)
                        
                        logger.info(f"Backfilled paper: {paper.arxiv_id}")
                        
                        # Send progress update
                        if self.progress_callback:
                            await self.progress_callback({
                                'type': 'paper_backfilled',
                                'paper_id': paper.arxiv_id,
                                'title': paper.title
                            })
                        
                        # Small delay between papers
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error backfilling paper {paper.arxiv_id}: {e}")
                
            except asyncio.CancelledError:
                logger.info("Backfill worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in backfill loop: {e}")
                await asyncio.sleep(60)
