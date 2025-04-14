from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import os
import json

from app.models.server import ServerMetrics
from app.services.data_processor.processor import DataProcessor
from app.services.clustering.optimized_clustering import OptimizedClusteringService
from app.services.evaluation.evaluation import EvaluationService
from app.services.recommendation.recommendation import RecommendationService

router = APIRouter()

processed_servers = []
clustering_service = OptimizedClusteringService(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
evaluation_service = EvaluationService()
recommendation_service = RecommendationService()

@router.post("/process-data")
async def process_data(data_path: str = "data/mcp_with_detailed_content.json"):
    """
    Process raw MCP server data from a JSON file.
    Default path is set to the full dataset file.
    """
    global processed_servers
    
    try:
        print(f"Processing data from: {data_path}")
        
        if not os.path.isabs(data_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            absolute_path = os.path.join(base_dir, data_path)
            print(f"Converting relative path to absolute: {absolute_path}")
        else:
            absolute_path = data_path
            
        if not os.path.exists(absolute_path):
            print(f"File not found at: {absolute_path}")
            alt_paths = [
                os.path.join(os.path.expanduser("~"), "mcp-analysis-system", data_path),
                os.path.join(os.path.expanduser("~"), data_path),
                os.path.join("/home/ubuntu/mcp-analysis-system", data_path),
                os.path.join(base_dir, "data", "mcp_with_detailed_content.json")  # Try the default location
            ]
            
            for path in alt_paths:
                print(f"Trying alternative path: {path}")
                if os.path.exists(path):
                    absolute_path = path
                    print(f"Found file at: {absolute_path}")
                    break
            else:
                raise FileNotFoundError(f"Could not find data file at any of the attempted paths")
        
        processor = DataProcessor(absolute_path)
        
        processor.load_data()
        processed_servers = processor.process_data()
        
        clustering_service.cluster_servers(processed_servers)
        
        evaluation_service.evaluate_servers(processed_servers)
        
        output_dir = os.path.dirname(absolute_path)
        output_path = os.path.join(output_dir, "processed_data.json")
        processor.save_processed_data(output_path)
        
        return {
            "message": "Data processed successfully",
            "server_count": len(processed_servers),
            "output_path": output_path
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing data: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@router.get("/status")
async def get_status():
    """获取数据处理状态"""
    if not processed_servers:
        raise HTTPException(status_code=503, detail="Data processing not completed")
    
    return {
        "status": "ready",
        "server_count": len(processed_servers),
        "has_clustering": any(server.cluster_id is not None for server in processed_servers),
        "has_evaluation": any(server.overall_score is not None for server in processed_servers)
    }

@router.get("/servers")
async def get_servers(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    cluster_id: Optional[int] = None
):
    """
    获取服务器列表，支持分页和搜索
    如果不提供limit，则返回所有数据
    """
    global processed_servers
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    filtered_servers = processed_servers
    
    # 应用过滤条件
    if cluster_id is not None:
        filtered_servers = [s for s in filtered_servers if s.cluster_id == cluster_id]
    
    if search:
        search_lower = search.lower()
        filtered_servers = [
            s for s in filtered_servers 
            if (
                search_lower in s.title.lower() or
                search_lower in s.description.lower() or
                any(search_lower in tag.lower() for tag in s.tags)
            )
        ]
    
    total = len(filtered_servers)
    
    # 应用分页
    if offset is not None:
        filtered_servers = filtered_servers[offset:]
    
    if limit is not None:
        filtered_servers = filtered_servers[:limit]
    
    return {
        "servers": filtered_servers,
        "total": total
    }

@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    """
    Get detailed information about a specific server.
    """
    global processed_servers
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    server = next((s for s in processed_servers if s.server_id == server_id), None)
    
    if not server:
        raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")
    
    similar_servers = clustering_service.get_similar_servers(server_id, processed_servers)
    
    server_dict = {
        "id": server.server_id,
        "title": server.title,
        "author": server.author,
        "description": server.description,
        "tags": server.tags,
        "word_count": server.word_count,
        "documentation_length": server.documentation_length,
        "feature_count": server.feature_count,
        "tool_count": server.tool_count,
        "has_github": server.has_github,
        "has_faq": server.has_faq,
        "cluster_id": server.cluster_id,
        "code_quality_score": server.code_quality_score,
        "tool_completeness_score": server.tool_completeness_score,
        "documentation_quality_score": server.documentation_quality_score,
        "runtime_stability_score": server.runtime_stability_score,
        "business_value_score": server.business_value_score,
        "overall_score": server.overall_score,
        "raw_data": server.raw_data,
        "similar_servers": similar_servers
    }
    
    return server_dict

@router.post("/cluster")
async def cluster_servers(similarity_threshold: float = 0.7):
    """
    Cluster servers based on entity linking.
    """
    global processed_servers, clustering_service
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    try:
        clustering_service.similarity_threshold = similarity_threshold
        
        clustered_servers = clustering_service.cluster_servers(processed_servers)
        
        visualization_data = clustering_service.generate_visualization_data(clustered_servers)
        
        cluster_summaries = clustering_service.get_cluster_summary(clustered_servers)
        
        cluster_count = len(set(server.cluster_id for server in clustered_servers if server.cluster_id is not None))
        
        return {
            "message": "Entity linking clustering completed successfully",
            "cluster_count": cluster_count,
            "visualization_data": visualization_data,
            "cluster_summaries": cluster_summaries
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error clustering servers: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Error clustering servers: {str(e)}")

@router.post("/evaluate")
async def evaluate_servers():
    """
    Evaluate servers based on quality criteria.
    """
    global processed_servers, evaluation_service
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    try:
        evaluated_servers = evaluation_service.evaluate_servers(processed_servers)
        
        evaluation_summary = evaluation_service.get_evaluation_summary(evaluated_servers)
        
        return {
            "message": "Evaluation completed successfully",
            "evaluation_summary": evaluation_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating servers: {str(e)}")

@router.get("/search")
async def search_servers(query: str, top_n: int = 5):
    """
    Search for servers matching a query.
    """
    global processed_servers, recommendation_service
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    try:
        search_results = recommendation_service.search_servers(query, processed_servers, top_n)
        
        return {
            "query": query,
            "results": search_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching servers: {str(e)}")

@router.get("/recommend")
async def recommend_servers(query: str, top_n: int = 3):
    """
    Get server recommendations based on a query.
    """
    global processed_servers, recommendation_service
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    try:
        recommendations = recommendation_service.get_recommendations(query, processed_servers, top_n)
        
        return {
            "query": query,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")

@router.post("/personalized-recommendations")
async def get_personalized_recommendations(user_preferences: Dict[str, Any], top_n: int = 3):
    """
    Get personalized server recommendations based on user preferences.
    """
    global processed_servers, recommendation_service
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    try:
        recommendations = recommendation_service.get_personalized_recommendations(
            user_preferences, processed_servers, top_n
        )
        
        return {
            "preferences": user_preferences,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting personalized recommendations: {str(e)}")
