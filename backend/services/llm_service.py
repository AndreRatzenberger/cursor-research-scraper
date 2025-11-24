"""LLM service with placeholder fallback support."""

import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations with graceful degradation."""
    
    def __init__(self):
        self.model_name = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        self.available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if LLM is available."""
        try:
            import litellm
            # Try a simple completion to check availability
            response = litellm.completion(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            self.available = True
            logger.info(f"LLM service available with model: {self.model_name}")
        except Exception as e:
            self.available = False
            logger.warning(f"LLM service unavailable: {e}")
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.available
    
    def generate_summary(self, title: str, abstract: str, 
                        full_text: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive summary of a paper."""
        if not self.available:
            logger.debug("LLM unavailable, returning placeholders")
            return {
                "summary": "<summary>",
                "keywords": ["<keywords>"],
                "key_contributions": "<key_contributions>",
                "methodology": "<methodology>",
                "results": "<results>",
                "future_research": "<future_research>"
            }
        
        try:
            import litellm
            
            # Build prompt
            content = f"Title: {title}\n\nAbstract: {abstract}"
            if full_text:
                content += f"\n\nFull Text: {full_text[:5000]}"  # Limit text length
            
            prompt = f"""Analyze this research paper and provide:
1. A concise summary (2-3 sentences)
2. Key keywords (5-7 words)
3. Key contributions (bullet points)
4. Methodology overview
5. Main results
6. Future research possibilities

Paper:
{content}

Respond in JSON format with keys: summary, keywords, key_contributions, methodology, results, future_research"""
            
            response = litellm.completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            import json
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Generated summary for paper: {title[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "summary": "<summary>",
                "keywords": ["<keywords>"],
                "key_contributions": "<key_contributions>",
                "methodology": "<methodology>",
                "results": "<results>",
                "future_research": "<future_research>"
            }
    
    def analyze_theory(self, hypothesis: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze papers for pro/contra arguments regarding a hypothesis."""
        if not self.available:
            logger.warning("LLM unavailable, cannot perform theory analysis")
            return []
        
        try:
            import litellm
            
            results = []
            for paper in papers:
                prompt = f"""Given this hypothesis: "{hypothesis}"

Analyze this research paper and determine:
1. Does it support (pro) or contradict (contra) the hypothesis?
2. What is the relevance score (0.0 to 1.0)?
3. What are the key arguments?
4. What are relevant quotes?

Paper:
Title: {paper['title']}
Abstract: {paper['abstract']}

Respond in JSON format with keys: stance (pro/contra), relevance_score, argument_summary, key_quotes"""
                
                response = litellm.completion(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                
                import json
                analysis = json.loads(response.choices[0].message.content)
                
                results.append({
                    "paper_id": paper['arxiv_id'],
                    "title": paper['title'],
                    "authors": paper['authors'],
                    "relevance_score": analysis.get('relevance_score', 0.5),
                    "argument_summary": analysis.get('argument_summary', ''),
                    "key_quotes": analysis.get('key_quotes', []),
                    "stance": analysis.get('stance', 'neutral')
                })
            
            logger.info(f"Analyzed {len(results)} papers for theory: {hypothesis[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing theory: {e}")
            return []
    
    def extract_relationships(self, paper1: Dict[str, Any], 
                            paper2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relationship between two papers."""
        if not self.available:
            return None
        
        try:
            import litellm
            
            prompt = f"""Analyze the relationship between these two papers:

Paper 1:
Title: {paper1['title']}
Abstract: {paper1['abstract']}

Paper 2:
Title: {paper2['title']}
Abstract: {paper2['abstract']}

Determine:
1. Relationship type (citation, topic_similarity, methodology_similarity, or none)
2. Strength (0.0 to 1.0)
3. Brief explanation

Respond in JSON format with keys: relationship_type, strength, explanation"""
            
            response = litellm.completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return None
