"""Graph service for managing paper relationships."""

import logging
from typing import List, Dict, Any, Optional
import networkx as nx

from backend.models.database import Database
from backend.models.schemas import Paper, Relationship
from backend.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class GraphService:
    """Service for managing the knowledge graph of papers."""
    
    def __init__(self, db: Database, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
        self.graph = nx.DiGraph()
    
    def build_graph(self):
        """Build the knowledge graph from papers and relationships."""
        logger.info("Building knowledge graph...")
        
        # Add papers as nodes
        papers = self.db.get_all_papers(limit=10000)
        for paper in papers:
            self.graph.add_node(
                paper.arxiv_id,
                title=paper.title,
                authors=paper.authors,
                categories=paper.categories
            )
        
        # Add relationships as edges
        all_relationships = []
        for paper in papers:
            relationships = self.db.get_relationships(paper.arxiv_id)
            all_relationships.extend(relationships)
        
        for rel in all_relationships:
            self.graph.add_edge(
                rel.source_id,
                rel.target_id,
                type=rel.relationship_type,
                strength=rel.strength,
                metadata=rel.metadata
            )
        
        logger.info(f"Graph built with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
    
    def discover_relationships(self, paper: Paper, all_papers: List[Paper]) -> List[Relationship]:
        """Discover relationships between a paper and others."""
        relationships = []
        
        # Check for shared authors
        for other_paper in all_papers:
            if other_paper.arxiv_id == paper.arxiv_id:
                continue
            
            # Shared authors
            shared_authors = set(paper.authors) & set(other_paper.authors)
            if shared_authors:
                relationships.append(Relationship(
                    source_id=paper.arxiv_id,
                    target_id=other_paper.arxiv_id,
                    relationship_type="shared_author",
                    strength=len(shared_authors) / max(len(paper.authors), len(other_paper.authors)),
                    metadata={"authors": list(shared_authors)}
                ))
            
            # Topic similarity via categories
            shared_categories = set(paper.categories) & set(other_paper.categories)
            if shared_categories:
                relationships.append(Relationship(
                    source_id=paper.arxiv_id,
                    target_id=other_paper.arxiv_id,
                    relationship_type="topic_similarity",
                    strength=len(shared_categories) / max(len(paper.categories), len(other_paper.categories)),
                    metadata={"categories": list(shared_categories)}
                ))
        
        logger.info(f"Discovered {len(relationships)} relationships for paper {paper.arxiv_id}")
        return relationships
    
    def find_similar_papers(self, arxiv_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar papers using embedding similarity."""
        paper_embedding = self.db.get_embedding(arxiv_id)
        if not paper_embedding:
            logger.warning(f"No embedding found for paper {arxiv_id}")
            return []
        
        # Get all embeddings
        all_embeddings = self.db.get_all_embeddings()
        
        similarities = []
        for emb_data in all_embeddings:
            other_id = emb_data['arxiv_id']
            if other_id == arxiv_id:
                continue
            
            similarity = self.embedding_service.compute_similarity(
                paper_embedding,
                emb_data['embedding']
            )
            
            similarities.append({
                'arxiv_id': other_id,
                'similarity': similarity
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Get paper details for top results
        results = []
        for sim in similarities[:limit]:
            paper = self.db.get_paper(sim['arxiv_id'])
            if paper:
                results.append({
                    'arxiv_id': paper.arxiv_id,
                    'title': paper.title,
                    'authors': paper.authors,
                    'similarity': sim['similarity']
                })
        
        logger.info(f"Found {len(results)} similar papers for {arxiv_id}")
        return results
    
    def get_paper_connections(self, arxiv_id: str) -> Dict[str, Any]:
        """Get all connections for a paper in the graph."""
        if arxiv_id not in self.graph:
            return {"nodes": [], "edges": []}
        
        # Get neighbors (1-hop connections)
        neighbors = list(self.graph.successors(arxiv_id)) + list(self.graph.predecessors(arxiv_id))
        neighbors = list(set(neighbors))  # Remove duplicates
        
        # Build subgraph
        subgraph_nodes = [arxiv_id] + neighbors
        subgraph = self.graph.subgraph(subgraph_nodes)
        
        # Format for visualization
        nodes = []
        for node in subgraph.nodes():
            node_data = self.graph.nodes[node]
            nodes.append({
                'id': node,
                'title': node_data.get('title', ''),
                'authors': node_data.get('authors', []),
                'categories': node_data.get('categories', [])
            })
        
        edges = []
        for source, target in subgraph.edges():
            edge_data = self.graph.edges[source, target]
            edges.append({
                'source': source,
                'target': target,
                'type': edge_data.get('type', ''),
                'strength': edge_data.get('strength', 1.0)
            })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            'total_nodes': len(self.graph.nodes),
            'total_edges': len(self.graph.edges),
            'density': nx.density(self.graph) if len(self.graph.nodes) > 0 else 0,
            'avg_degree': sum(dict(self.graph.degree()).values()) / len(self.graph.nodes) if len(self.graph.nodes) > 0 else 0
        }
