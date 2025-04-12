from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from app.api.endpoints import router as api_router
from app.api.endpoints import process_data

app = FastAPI(title="MCP Server Analysis System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://mcp-server-app-42rhe1o4.devinapps.com"],
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

@app.on_event("startup")
async def startup_event():
    """Process data on startup to avoid CORS issues with the button click."""
    try:
        print("Pre-processing MCP server data on startup...")
        await process_data()
        print("Data pre-processing completed successfully!")
    except Exception as e:
        print(f"Error during startup data processing: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
