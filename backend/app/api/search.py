from fastapi import APIRouter, Query
from typing import Optional
from app.services.search_service import search_service

router = APIRouter()

@router.get("/clusters/search")
async def search_clusters(
    query: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(15, ge=1, le=100, description="每页数量")
):
    """
    搜索集群
    
    参数:
    - query: 搜索关键词
    - page: 页码（从1开始）
    - page_size: 每页显示数量
    
    返回:
    - items: 集群列表
    - total: 总数
    - page: 当前页码
    - page_size: 每页数量
    """
    return search_service.search(
        query=query or '',
        page=page,
        page_size=page_size
    ) 