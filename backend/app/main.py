from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os

from app.api.endpoints import router as api_router
from app.api.endpoints import process_data
from app.utils.progress_manager import ProgressManager

app = FastAPI(title="MCP Server Analysis System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173", "https://mcp-server-app-42rhe1o4.devinapps.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
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
    """Process data on startup to avoid CORS issues with the button click."""
    try:
        print("\n=== 系统启动，开始数据预处理 ===")
        
        # 检查是否需要处理数据
        progress_manager = ProgressManager(os.path.join(os.path.dirname(__file__), "..", "data"))
        
        # 验证缓存完整性
        if not progress_manager.verify_cache_integrity():
            print("缓存完整性验证失败，重置进度...")
            progress_manager.reset_progress()
        
        progress = progress_manager.get_progress()
        
        if len(progress['completed_stages']) == len(ProgressManager.STAGES):
            print("所有数据处理阶段已完成，无需重新处理")
            return
        
        print(f"当前处理进度:")
        print(f"- 已完成阶段: {', '.join(progress['completed_stages']) if progress['completed_stages'] else '无'}")
        print(f"- 当前阶段: {progress['current_stage'] if progress['current_stage'] else '无'}")
        
        await process_data()
        print("数据预处理完成!")
        
    except Exception as e:
        print(f"启动时数据处理出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
