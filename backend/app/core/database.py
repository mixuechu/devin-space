from pymongo import MongoClient
from typing import Dict, List, Optional, Any
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # MongoDB connection
    client = MongoClient('mongodb://localhost:27017/')
    db = client['server_explorer']
    servers_collection = db['servers']
    clusters_collection = db['clusters']
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

def load_raw_server_data() -> List[Dict]:
    """Load server data from JSON file"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                            'mcp_with_detailed_content.json')
    with open(data_file, 'r') as f:
        return json.load(f)

def init_db():
    """Initialize database connection and create necessary indexes"""
    try:
        # 检查数据库连接
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # 删除并重新创建集合
        logger.info("Dropping existing collections...")
        db.drop_collection("clusters")
        db.drop_collection("servers")
        
        logger.info("Creating new collections...")
        db.create_collection("clusters")
        db.create_collection("servers")
        
        # 创建新索引
        logger.info("Creating indexes...")
        # 使用复合索引，cluster_id保持唯一性，cluster_name用于搜索
        clusters_collection.create_index([('cluster_id', 1)], unique=True, name="cluster_id_1")
        clusters_collection.create_index([('cluster_name', 1)], name="cluster_name_1")  # 移除unique=True
        
        # 创建服务器集合的索引
        servers_collection.create_index([('server_id', 1)], unique=True, name="server_id_1")
        servers_collection.create_index([('cluster_id', 1)], name="cluster_id_1")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

def save_cluster(cluster_data: Dict[str, Any]):
    """
    Save or update cluster information in the database.
    
    Args:
        cluster_data: Dictionary containing cluster information
    """
    try:
        cluster_id = cluster_data['cluster_id']
        logger.info(f"Saving cluster {cluster_id} to database")
        result = clusters_collection.update_one(
            {'cluster_id': cluster_id},
            {'$set': cluster_data},
            upsert=True
        )
        logger.info(f"Cluster {cluster_id} saved successfully (matched: {result.matched_count}, modified: {result.modified_count}, upserted: {result.upserted_id is not None})")
    except Exception as e:
        logger.error(f"Error saving cluster: {str(e)}")
        raise

def get_cluster(cluster_id: int) -> Optional[Dict[str, Any]]:
    """
    Get cluster information from the database.
    
    Args:
        cluster_id: ID of the cluster
        
    Returns:
        Cluster information or None if not found
    """
    try:
        cluster = clusters_collection.find_one({'cluster_id': cluster_id}, {'_id': 0})
        if cluster:
            logger.info(f"Retrieved cluster {cluster_id}")
        else:
            logger.info(f"Cluster {cluster_id} not found")
        return cluster
    except Exception as e:
        logger.error(f"Error retrieving cluster: {str(e)}")
        raise

def get_all_clusters() -> List[Dict[str, Any]]:
    """
    Get all clusters from the database.
    
    Returns:
        List of cluster information
    """
    try:
        clusters = list(clusters_collection.find({}, {'_id': 0}))
        logger.info(f"Retrieved {len(clusters)} clusters")
        return clusters
    except Exception as e:
        logger.error(f"Error retrieving clusters: {str(e)}")
        raise

def get_servers(page: int = 1, page_size: int = 30, cluster_id: Optional[str] = None) -> Dict:
    """Get paginated servers with optional cluster filter"""
    query = {'cluster_id': cluster_id} if cluster_id else {}
    
    # Get servers with pagination
    servers = list(servers_collection.find(
        query,
        {'_id': 0}  # Exclude MongoDB _id field
    ).skip((page - 1) * page_size).limit(page_size))
    
    # Get total count for pagination
    total = servers_collection.count_documents(query)
    
    return {
        'servers': servers,
        'total': total,
        'page': page,
        'page_size': page_size
    }

def get_server_by_id(server_id: str) -> Optional[Dict]:
    """Get a single server by ID"""
    return servers_collection.find_one(
        {'server_id': server_id},
        {'_id': 0}  # Exclude MongoDB _id field
    ) 