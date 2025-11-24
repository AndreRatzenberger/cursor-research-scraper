"""ArXiv paper fetching and processing service."""

import logging
from typing import List, Optional
import arxiv
from PyPDF2 import PdfReader
import io
import requests

from backend.models.schemas import Paper

logger = logging.getLogger(__name__)


class ArxivService:
    """Service for fetching papers from arXiv."""
    
    def __init__(self):
        self.client = arxiv.Client()
    
    def fetch_paper(self, arxiv_id: str) -> Optional[Paper]:
        """Fetch a single paper by arXiv ID."""
        try:
            # Clean arXiv ID (remove version if present)
            clean_id = arxiv_id.split('v')[0]
            
            search = arxiv.Search(id_list=[clean_id])
            results = list(self.client.results(search))
            
            if not results:
                logger.warning(f"No paper found for arXiv ID: {arxiv_id}")
                return None
            
            result = results[0]
            
            # Extract metadata
            paper = Paper(
                arxiv_id=result.entry_id.split('/')[-1],
                title=result.title,
                authors=[author.name for author in result.authors],
                abstract=result.summary,
                published=result.published.isoformat(),
                categories=[cat for cat in result.categories],
                pdf_url=result.pdf_url,
                needs_backfill=True  # LLM fields need processing
            )
            
            logger.info(f"Fetched paper: {paper.arxiv_id} - {paper.title}")
            return paper
            
        except Exception as e:
            logger.error(f"Error fetching paper {arxiv_id}: {e}")
            return None
    
    def fetch_latest_papers(self, category: Optional[str] = None, 
                           max_results: int = 10) -> List[Paper]:
        """Fetch latest papers from arXiv."""
        try:
            # Build search query
            query = f"cat:{category}" if category else "all"
            
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            for result in self.client.results(search):
                paper = Paper(
                    arxiv_id=result.entry_id.split('/')[-1],
                    title=result.title,
                    authors=[author.name for author in result.authors],
                    abstract=result.summary,
                    published=result.published.isoformat(),
                    categories=[cat for cat in result.categories],
                    pdf_url=result.pdf_url,
                    needs_backfill=True
                )
                papers.append(paper)
            
            logger.info(f"Fetched {len(papers)} latest papers" + 
                       (f" for category {category}" if category else ""))
            return papers
            
        except Exception as e:
            logger.error(f"Error fetching latest papers: {e}")
            return []
    
    def search_papers(self, query: str, max_results: int = 10) -> List[Paper]:
        """Search papers by text query."""
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            papers = []
            for result in self.client.results(search):
                paper = Paper(
                    arxiv_id=result.entry_id.split('/')[-1],
                    title=result.title,
                    authors=[author.name for author in result.authors],
                    abstract=result.summary,
                    published=result.published.isoformat(),
                    categories=[cat for cat in result.categories],
                    pdf_url=result.pdf_url,
                    needs_backfill=True
                )
                papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers for query: {query}")
            return papers
            
        except Exception as e:
            logger.error(f"Error searching papers: {e}")
            return []
    
    def extract_pdf_text(self, pdf_url: str) -> Optional[str]:
        """Extract text from PDF URL."""
        try:
            # Download PDF
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Extract text
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)
            
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting PDF text from {pdf_url}: {e}")
            return None
