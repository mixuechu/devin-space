from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
from typing import Optional
from .core.database import init_db

from app.api.endpoints import router as api_router, processed_servers, process_data
from app.utils.progress_manager import ProgressManager
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server Analysis System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to MCP Server Analysis System API"}

@app.get("/status")
async def get_status():
    """获取数据处理进度"""
    progress_manager = ProgressManager(os.path.join(os.path.dirname(__file__), "..", "data"))
    progress = progress_manager.get_progress()
    
    # 计算总体进度百分比
    total_stages = len(ProgressManager.STAGES)
    completed_stages = len(progress['completed_stages'])
    current_stage = progress['current_stage']
    
    if current_stage:
        stage_progress = progress['processed_count'] / max(progress['total_count'], 1) if progress['total_count'] > 0 else 0
        overall_progress = (completed_stages + stage_progress) / total_stages
    else:
        overall_progress = completed_stages / total_stages
    
    return {
        "current_stage": current_stage,
        "completed_stages": progress['completed_stages'],
        "stage_progress": {
            "processed": progress['processed_count'],
            "total": progress['total_count']
        },
        "overall_progress": overall_progress,
        "last_updated": progress['last_updated']
    }

@app.on_event("startup")
async def startup_event():
    """Initialize database and process data on application startup"""
    try:
        # 初始化数据库
        init_db()
        logger.info("数据库初始化完成")
        
        # 自动加载数据
        if not processed_servers:
            logger.info("开始自动加载数据...")
            try:
                await process_data()
                logger.info("数据加载完成")
            except Exception as e:
                logger.error(f"自动加载数据失败: {e}")
                # 继续启动，即使数据加载失败
                pass
        else:
            logger.info("数据已加载，跳过自动加载")
    except Exception as e:
        logger.error(f"启动事件出错: {e}")
        # 继续启动，不中断服务

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
