from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import search
from app.services.search_service import search_service
from app.services.clustering import get_clustering_data

app = FastAPI(title="MCP Server Analysis API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(search.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化搜索服务"""
    # 获取集群数据
    clustering_data = await get_clustering_data(threshold=0.7)
    if clustering_data and clustering_data.cluster_summaries:
        # 构建搜索索引
        search_service.build_index(clustering_data.cluster_summaries)

@app.get("/")
async def root():
    return {"message": "MCP Server Analysis API"}
