from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class MCPServer(BaseModel):
    """Model representing an MCP server from the raw data."""
    id: str
    type: str
    title: str
    author: str
    description: str
    tags: List[str]
    github_url: Optional[str] = None
    page_url: Optional[str] = None
    page: int
    timestamp: datetime
    content: str
    detailed_content: str

class ServerMetrics(BaseModel):
    """Model representing extracted metrics from an MCP server."""
    server_id: str
    title: str
    author: str
    description: str
    tags: List[str]
    
    word_count: int
    documentation_length: int
    feature_count: int
    tool_count: int
    has_github: bool
    has_faq: bool
    
    feature_vector: List[float]
    
    code_quality_score: Optional[float] = None
    tool_completeness_score: Optional[float] = None
    documentation_quality_score: Optional[float] = None
    runtime_stability_score: Optional[float] = None
    business_value_score: Optional[float] = None
    overall_score: Optional[float] = None
    
    cluster_id: Optional[int] = None
    
    raw_data: Dict[str, Any]
