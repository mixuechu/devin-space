from typing import List, Optional
from pydantic import BaseModel

class Server(BaseModel):
    """服务器模型"""
    id: str
    title: str
    description: str
    tags: List[str]
    cluster_id: Optional[int] = None

class ClusterSummary(BaseModel):
    """集群摘要模型"""
    cluster_id: int
    cluster_name: str
    description: Optional[str] = None
    common_tags: List[str]
    servers: List[Server]
    visualization_coords: Optional[List[float]] = None

class ClusteringData(BaseModel):
    """聚类数据模型"""
    visualization_data: List[List[float]]
    cluster_summaries: List[ClusterSummary] 