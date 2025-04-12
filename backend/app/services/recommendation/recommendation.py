from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re

from app.models.server import ServerMetrics

class RecommendationService:
    """
    Service for recommending MCP servers based on user queries and preferences.
    """
    
    def __init__(self):
        """
        Initialize the recommendation service.
        """
        self.ai_model_available = False
    
    def search_servers(self, query: str, servers: List[ServerMetrics], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Search for servers matching a user query.
        
        Args:
            query: User search query.
            servers: List of ServerMetrics objects.
            top_n: Number of results to return.
            
        Returns:
            List of dictionaries containing search results.
        """
        query = query.lower()
        query_terms = query.split()
        
        results = []
        for server in servers:
            title = server.title.lower()
            description = server.description.lower()
            tags = [tag.lower() for tag in server.tags]
            
            score = 0.0
            
            for term in query_terms:
                if term in title:
                    score += 3.0
            
            for term in query_terms:
                if term in description:
                    score += 1.0
            
            for term in query_terms:
                for tag in tags:
                    if term in tag:
                        score += 2.0
            
            if server.overall_score is not None:
                score += (server.overall_score / 100.0) * 2.0
            
            if score > 0:
                results.append({
                    "id": server.server_id,
                    "title": server.title,
                    "description": server.description,
                    "tags": server.tags,
                    "relevance_score": score,
                    "quality_score": server.overall_score
                })
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return results[:top_n]
    
    def get_recommendations(self, query: str, servers: List[ServerMetrics], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Get server recommendations based on a user query.
        
        Args:
            query: User search query.
            servers: List of ServerMetrics objects.
            top_n: Number of recommendations to return.
            
        Returns:
            List of dictionaries containing recommendations.
        """
        search_results = self.search_servers(query, servers, top_n=top_n)
        
        if len(search_results) >= top_n:
            return search_results
        
        return self._get_advanced_recommendations(query, servers, search_results, top_n)
    
    def _get_advanced_recommendations(
        self, 
        query: str, 
        servers: List[ServerMetrics], 
        existing_results: List[Dict[str, Any]], 
        top_n: int
    ) -> List[Dict[str, Any]]:
        """
        Get advanced recommendations when direct search doesn't yield enough results.
        
        Args:
            query: User search query.
            servers: List of ServerMetrics objects.
            existing_results: Results from direct search.
            top_n: Number of recommendations to return.
            
        Returns:
            List of dictionaries containing recommendations.
        """
        existing_ids = [result["id"] for result in existing_results]
        
        query = query.lower()
        
        additional_results = []
        
        for server in servers:
            if server.server_id in existing_ids:
                continue
            
            title = server.title.lower()
            description = server.description.lower()
            content = server.raw_data["content"].lower()
            
            score = 0.0
            
            related_terms = self._get_related_terms(query)
            for term in related_terms:
                if term in title:
                    score += 1.5
                if term in description:
                    score += 1.0
                if term in content:
                    score += 0.5
            
            if server.overall_score is not None:
                score += (server.overall_score / 100.0)
            
            if score > 0:
                additional_results.append({
                    "id": server.server_id,
                    "title": server.title,
                    "description": server.description,
                    "tags": server.tags,
                    "relevance_score": score,
                    "quality_score": server.overall_score,
                    "is_ai_recommendation": True
                })
        
        additional_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        combined_results = existing_results + additional_results
        
        return combined_results[:top_n]
    
    def _get_related_terms(self, query: str) -> List[str]:
        """
        Get related terms for a query to improve semantic matching.
        
        Args:
            query: User search query.
            
        Returns:
            List of related terms.
        """
        related_terms = [query]
        
        related_terms.extend(query.split())
        
        if "github" in query.lower():
            related_terms.extend(["git", "repository", "code", "development"])
        
        if "map" in query.lower():
            related_terms.extend(["location", "navigation", "geographic", "gps"])
        
        if "database" in query.lower() or "redis" in query.lower():
            related_terms.extend(["storage", "data", "cache", "nosql", "db"])
        
        if "browser" in query.lower() or "playwright" in query.lower():
            related_terms.extend(["automation", "web", "testing", "scraping"])
        
        if "3d" in query.lower() or "blender" in query.lower():
            related_terms.extend(["modeling", "rendering", "visualization", "graphics"])
        
        if "time" in query.lower():
            related_terms.extend(["date", "timezone", "clock", "schedule"])
        
        related_terms = list(set(related_terms))
        
        return related_terms
    
    def get_personalized_recommendations(
        self, 
        user_preferences: Dict[str, Any], 
        servers: List[ServerMetrics], 
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get personalized server recommendations based on user preferences.
        
        Args:
            user_preferences: Dictionary containing user preferences.
            servers: List of ServerMetrics objects.
            top_n: Number of recommendations to return.
            
        Returns:
            List of dictionaries containing personalized recommendations.
        """
        weights = user_preferences.get("weights", {
            "code_quality": 1.0,
            "tool_completeness": 1.0,
            "documentation_quality": 1.0,
            "runtime_stability": 1.0,
            "business_value": 1.0
        })
        
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        results = []
        for server in servers:
            if (server.code_quality_score is None or
                server.tool_completeness_score is None or
                server.documentation_quality_score is None or
                server.runtime_stability_score is None or
                server.business_value_score is None):
                continue
            
            score = (
                weights.get("code_quality", 0.2) * server.code_quality_score +
                weights.get("tool_completeness", 0.2) * server.tool_completeness_score +
                weights.get("documentation_quality", 0.2) * server.documentation_quality_score +
                weights.get("runtime_stability", 0.2) * server.runtime_stability_score +
                weights.get("business_value", 0.2) * server.business_value_score
            )
            
            preferred_tags = user_preferences.get("preferred_tags", [])
            for tag in server.tags:
                if tag.lower() in [t.lower() for t in preferred_tags]:
                    score += 5.0
            
            results.append({
                "id": server.server_id,
                "title": server.title,
                "description": server.description,
                "tags": server.tags,
                "personalized_score": score,
                "quality_scores": {
                    "code_quality": server.code_quality_score,
                    "tool_completeness": server.tool_completeness_score,
                    "documentation_quality": server.documentation_quality_score,
                    "runtime_stability": server.runtime_stability_score,
                    "business_value": server.business_value_score
                }
            })
        
        results.sort(key=lambda x: x["personalized_score"], reverse=True)
        
        return results[:top_n]
