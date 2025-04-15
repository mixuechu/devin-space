from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import os
import json
from thefuzz import fuzz  # 添加模糊匹配库
import logging
import shutil
from pymongo.errors import DuplicateKeyError

from app.models.server import ServerMetrics
from app.services.data_processor.processor import DataProcessor
from app.services.clustering.optimized_clustering import OptimizedClusteringService as ClusteringService
from app.services.evaluation.evaluation import EvaluationService
from app.services.recommendation.recommendation import RecommendationService
from app.services.search_service import search_service
from app.core.database import get_all_clusters, get_cluster, save_cluster, clusters_collection, servers_collection

logger = logging.getLogger(__name__)

router = APIRouter()

# Make processed_servers accessible from outside
processed_servers: List[ServerMetrics] = []

clustering_service = ClusteringService(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
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
        
        # 重建索引以确保唯一性
        try:
            # 删除现有的cluster_name索引
            clusters_collection.drop_index("cluster_name_1")
        except Exception as e:
            logger.info("No existing cluster_name index to drop")
        
        # 创建新的非唯一索引
        clusters_collection.create_index([('cluster_name', 1)], unique=False, name="cluster_name_1")
        
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
        
        print("Loading data...")  # Debug log
        processor.load_data()
        processed_servers = processor.process_data()
        print(f"Processed {len(processed_servers)} servers")  # Debug log
        
        # 执行集群分析
        print("Starting initial clustering...")  # Debug log
        clustered_servers = clustering_service.cluster_servers(processed_servers)
        print(f"Clustered {len(clustered_servers)} servers")  # Debug log
        
        # 验证集群分配
        cluster_count = len(set(server.cluster_id for server in clustered_servers if server.cluster_id is not None))
        print(f"Created {cluster_count} clusters")  # Debug log
        
        # 生成并保存集群信息
        cluster_servers_map = {}
        for server in clustered_servers:
            if server.cluster_id is not None:
                if server.cluster_id not in cluster_servers_map:
                    cluster_servers_map[server.cluster_id] = []
                cluster_servers_map[server.cluster_id].append(server)
        
        for cluster_id, servers in cluster_servers_map.items():
            # 获取集群中所有服务器的标题
            titles = [server.title for server in servers]
            cluster_name = clustering_service.extract_cluster_name(titles)
            
            # 计算统计信息
            avg_word_count = sum(server.word_count for server in servers) / len(servers)
            avg_feature_count = sum(server.feature_count for server in servers) / len(servers)
            avg_tool_count = sum(server.tool_count for server in servers) / len(servers)
            
            # 收集标签
            all_tags = []
            for server in servers:
                all_tags.extend(server.tags)
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            common_tags = [tag for tag, _ in common_tags]
            
            cluster_data = {
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "size": len(servers),
                "servers": [{"id": server.server_id, "title": server.title} for server in servers],
                "avg_word_count": float(avg_word_count),
                "avg_feature_count": float(avg_feature_count),
                "avg_tool_count": float(avg_tool_count),
                "common_tags": common_tags
            }
            
            try:
                # 使用cluster_id作为唯一标识进行更新
                result = clusters_collection.replace_one(
                    {"cluster_id": cluster_id},
                    cluster_data,
                    upsert=True
                )
                logger.info(f"Saved cluster {cluster_id} with name '{cluster_name}'")
            except Exception as e:
                logger.error(f"保存集群 {cluster_id} ('{cluster_name}') 时出错: {str(e)}")
                continue
        
        # 构建搜索索引
        print("Building search index...")  # Debug log
        search_service.build_index([])
        
        return {
            "message": "Data processing completed successfully",
            "server_count": len(processed_servers),
            "cluster_count": cluster_count
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
    page: Optional[int] = 1,
    page_size: Optional[int] = 30,
    search: Optional[str] = None,
    cluster_id: Optional[int] = None
):
    """
    获取服务器列表，支持分页和搜索
    
    改进:
    1. 添加模糊匹配
    2. 计算相关性得分
    3. 按相关性排序
    """
    global processed_servers
    
    if not processed_servers:
        raise HTTPException(status_code=404, detail="No processed data available")
    
    filtered_servers = processed_servers
    
    # 应用集群过滤
    if cluster_id is not None:
        filtered_servers = [s for s in filtered_servers if s.cluster_id == cluster_id]
    
    # 改进的搜索逻辑
    if search:
        search_lower = search.lower()
        search_words = search_lower.split()
        
        # 存储服务器和其搜索得分
        scored_servers = []
        
        for server in filtered_servers:
            total_score = 0
            
            # 计算标题的匹配得分
            title_score = max(
                fuzz.partial_ratio(search_lower, server.title.lower()),
                max((fuzz.ratio(word, server.title.lower()) for word in search_words), default=0)
            )
            total_score += title_score * 2  # 标题匹配权重加倍
            
            # 计算描述的匹配得分
            desc_score = max(
                fuzz.partial_ratio(search_lower, server.description.lower()),
                max((fuzz.ratio(word, server.description.lower()) for word in search_words), default=0)
            )
            total_score += desc_score
            
            # 计算标签的匹配得分
            tag_scores = []
            for tag in server.tags:
                tag_score = max(
                    fuzz.partial_ratio(search_lower, tag.lower()),
                    max((fuzz.ratio(word, tag.lower()) for word in search_words), default=0)
                )
                tag_scores.append(tag_score)
            
            if tag_scores:
                total_score += max(tag_scores) * 1.5  # 标签匹配权重提升
            
            # 如果有质量评分，将其纳入考虑
            if hasattr(server, 'overall_score') and server.overall_score is not None:
                total_score += (server.overall_score / 100.0) * 20  # 质量评分权重
            
            # 只保留相关性超过阈值的结果
            if total_score > 50:  # 相关性阈值
                scored_servers.append((server, total_score))
        
        # 按得分排序
        scored_servers.sort(key=lambda x: x[1], reverse=True)
        filtered_servers = [server for server, _ in scored_servers]
    
    total = len(filtered_servers)
    
    # 应用分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_servers = filtered_servers[start_idx:end_idx]
    
    return {
        "servers": paginated_servers,
        "total": total,
        "page": page,
        "page_size": page_size
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
    Cluster servers based on their features
    """
    try:
        global processed_servers
        
        if not processed_servers:
            raise HTTPException(status_code=404, detail="No processed data available")
            
        # 清理现有的集群数据
        clusters_collection.drop()
        clusters_collection.create_index('cluster_id', unique=True)
        clusters_collection.create_index('cluster_name', unique=False)  # 确保不是唯一索引
        
        # 清理服务器的集群信息
        servers_collection.update_many({}, {'$unset': {'cluster_id': "", 'cluster_name': ""}})
        
        # 使用全局变量
        servers = processed_servers
        
        # 执行聚类
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        clustering_service = ClusteringService(data_dir=data_dir)
        clustered_servers = clustering_service.cluster_servers(servers)
        
        # 生成可视化数据
        visualization_data = clustering_service.generate_visualization_data(servers)
        
        # 获取集群摘要
        cluster_summaries = clustering_service.get_cluster_summary(servers)
        
        # 保存集群信息到数据库
        for summary in cluster_summaries:
            save_cluster(summary)
        
        return {
            "visualization_data": visualization_data,
            "cluster_summaries": cluster_summaries
        }
    except Exception as e:
        logger.error(f"Error in cluster_servers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/clean")
async def clean_data(
    clean_cache: bool = True,
    clean_db: bool = True
):
    """
    清理系统数据
    
    Args:
        clean_cache: 是否清理缓存文件
        clean_db: 是否清理数据库
    """
    try:
        if clean_cache:
            # 清理中间文件
            logger.info("清理缓存文件...")
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            intermediate_dir = os.path.join(data_dir, "intermediate")
            progress_file = os.path.join(data_dir, "processing_progress.json")
            
            if os.path.exists(intermediate_dir):
                shutil.rmtree(intermediate_dir)
                os.makedirs(intermediate_dir)
            
            if os.path.exists(progress_file):
                os.remove(progress_file)
        
        if clean_db:
            # 清理数据库
            logger.info("清理数据库...")
            clusters_collection.drop()
            clusters_collection.create_index('cluster_id', unique=True)
            clusters_collection.create_index('cluster_name')
            servers_collection.update_many({}, {'$unset': {'cluster_id': "", 'cluster_name': ""}})
        
        return {
            "message": "清理完成",
            "cleaned_cache": clean_cache,
            "cleaned_db": clean_db
        }
    except Exception as e:
        logger.error(f"清理数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
