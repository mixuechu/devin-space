from typing import List, Dict, Any, Optional
import numpy as np
import re

from app.models.server import ServerMetrics

class EvaluationService:
    """
    Service for evaluating MCP servers based on quality criteria.
    """
    
    def __init__(self):
        """
        Initialize the evaluation service with weights for different criteria.
        """
        self.weights = {
            "code_quality": 0.25,
            "tool_completeness": 0.20,
            "documentation_quality": 0.20,
            "runtime_stability": 0.15,
            "business_value": 0.20
        }
    
    def evaluate_servers(self, servers: List[ServerMetrics]) -> List[ServerMetrics]:
        """
        Evaluate servers based on quality criteria.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            List of ServerMetrics objects with evaluation scores.
        """
        for server in servers:
            code_quality_score = self._evaluate_code_quality(server)
            tool_completeness_score = self._evaluate_tool_completeness(server)
            documentation_quality_score = self._evaluate_documentation_quality(server)
            runtime_stability_score = self._evaluate_runtime_stability(server)
            business_value_score = self._evaluate_business_value(server)
            
            server.code_quality_score = code_quality_score
            server.tool_completeness_score = tool_completeness_score
            server.documentation_quality_score = documentation_quality_score
            server.runtime_stability_score = runtime_stability_score
            server.business_value_score = business_value_score
            
            server.overall_score = (
                self.weights["code_quality"] * code_quality_score +
                self.weights["tool_completeness"] * tool_completeness_score +
                self.weights["documentation_quality"] * documentation_quality_score +
                self.weights["runtime_stability"] * runtime_stability_score +
                self.weights["business_value"] * business_value_score
            )
        
        return servers
    
    def _evaluate_code_quality(self, server: ServerMetrics) -> float:
        """
        Evaluate code quality based on server metrics.
        
        Args:
            server: ServerMetrics object.
            
        Returns:
            Score for code quality (0-100).
        """
        score = 60.0
        
        if server.has_github:
            score += 10.0
        
        content = server.raw_data["detailed_content"].lower()
        if "```" in content or "example" in content or "code" in content:
            score += 10.0
        
        if "error" in content or "exception" in content or "try" in content or "catch" in content:
            score += 10.0
        
        if "performance" in content or "optimize" in content or "efficient" in content:
            score += 5.0
        
        if "best practice" in content or "pattern" in content or "standard" in content:
            score += 5.0
        
        return min(score, 100.0)
    
    def _evaluate_tool_completeness(self, server: ServerMetrics) -> float:
        """
        Evaluate tool completeness based on server metrics.
        
        Args:
            server: ServerMetrics object.
            
        Returns:
            Score for tool completeness (0-100).
        """
        score = 50.0
        
        score += min(server.tool_count * 5.0, 20.0)
        
        content = server.raw_data["detailed_content"].lower()
        if "api" in content or "interface" in content or "endpoint" in content:
            score += 10.0
        
        if "extend" in content or "plugin" in content or "custom" in content:
            score += 10.0
        
        if "feature" in content or "capability" in content or "function" in content:
            score += 10.0
        
        return min(score, 100.0)
    
    def _evaluate_documentation_quality(self, server: ServerMetrics) -> float:
        """
        Evaluate documentation quality based on server metrics.
        
        Args:
            server: ServerMetrics object.
            
        Returns:
            Score for documentation quality (0-100).
        """
        score = 40.0
        
        doc_length_score = min(server.documentation_length / 100.0, 15.0)
        score += doc_length_score
        
        if server.has_faq:
            score += 15.0
        
        content = server.raw_data["detailed_content"].lower()
        if "example" in content or "usage" in content:
            score += 10.0
        
        if "install" in content or "setup" in content or "configuration" in content:
            score += 10.0
        
        if re.search(r"#+\s+\w+", content) or re.search(r"\n\w+\n[-=]+", content):
            score += 10.0
        
        return min(score, 100.0)
    
    def _evaluate_runtime_stability(self, server: ServerMetrics) -> float:
        """
        Evaluate runtime stability based on server metrics.
        
        Args:
            server: ServerMetrics object.
            
        Returns:
            Score for runtime stability (0-100).
        """
        score = 70.0
        
        content = server.raw_data["detailed_content"].lower()
        if "error" in content or "exception" in content or "handle" in content:
            score += 10.0
        
        if "test" in content or "unit test" in content or "integration test" in content:
            score += 10.0
        
        if "version" in content or "release" in content or "stable" in content:
            score += 5.0
        
        if "compatible" in content or "environment" in content or "platform" in content:
            score += 5.0
        
        return min(score, 100.0)
    
    def _evaluate_business_value(self, server: ServerMetrics) -> float:
        """
        Evaluate business value based on server metrics.
        
        Args:
            server: ServerMetrics object.
            
        Returns:
            Score for business value (0-100).
        """
        score = 60.0
        
        content = server.raw_data["detailed_content"].lower()
        if "use case" in content or "application" in content or "scenario" in content:
            score += 15.0
        
        if "integrate" in content or "connect" in content or "interface with" in content:
            score += 10.0
        
        if "time" in content or "cost" in content or "efficient" in content or "save" in content:
            score += 10.0
        
        if "unique" in content or "novel" in content or "innovative" in content:
            score += 5.0
        
        return min(score, 100.0)
    
    def get_evaluation_summary(self, servers: List[ServerMetrics]) -> Dict[str, Any]:
        """
        Generate summary statistics for server evaluations.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            Dictionary containing evaluation summary statistics.
        """
        if not servers:
            return {}
        
        avg_overall = np.mean([server.overall_score for server in servers if server.overall_score is not None])
        avg_code_quality = np.mean([server.code_quality_score for server in servers if server.code_quality_score is not None])
        avg_tool_completeness = np.mean([server.tool_completeness_score for server in servers if server.tool_completeness_score is not None])
        avg_documentation_quality = np.mean([server.documentation_quality_score for server in servers if server.documentation_quality_score is not None])
        avg_runtime_stability = np.mean([server.runtime_stability_score for server in servers if server.runtime_stability_score is not None])
        avg_business_value = np.mean([server.business_value_score for server in servers if server.business_value_score is not None])
        
        top_servers = sorted(servers, key=lambda x: x.overall_score if x.overall_score is not None else 0, reverse=True)[:5]
        top_server_info = [{"id": server.server_id, "title": server.title, "score": server.overall_score} for server in top_servers]
        
        summary = {
            "average_scores": {
                "overall": avg_overall,
                "code_quality": avg_code_quality,
                "tool_completeness": avg_tool_completeness,
                "documentation_quality": avg_documentation_quality,
                "runtime_stability": avg_runtime_stability,
                "business_value": avg_business_value
            },
            "top_servers": top_server_info,
            "score_distribution": {
                "excellent": len([s for s in servers if s.overall_score is not None and s.overall_score >= 90]),
                "good": len([s for s in servers if s.overall_score is not None and 80 <= s.overall_score < 90]),
                "average": len([s for s in servers if s.overall_score is not None and 70 <= s.overall_score < 80]),
                "below_average": len([s for s in servers if s.overall_score is not None and 60 <= s.overall_score < 70]),
                "poor": len([s for s in servers if s.overall_score is not None and s.overall_score < 60])
            }
        }
        
        return summary
