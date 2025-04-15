from pymongo import MongoClient
from typing import Dict, List, Optional
import json
import os

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['server_explorer']
servers_collection = db['servers']
clusters_collection = db['clusters']

def load_raw_server_data() -> List[Dict]:
    """Load server data from JSON file"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                            'mcp_with_detailed_content.json')
    with open(data_file, 'r') as f:
        return json.load(f)

def init_db():
    """Initialize database with server and cluster data"""
    # Only initialize if database is empty
    if servers_collection.count_documents({}) == 0:
        # Load and process raw data
        servers = load_raw_server_data()
        
        # Insert servers first
        servers_collection.insert_many(servers)
        
        # Create indices for better query performance
        servers_collection.create_index('server_id')
        servers_collection.create_index('cluster_id')
        servers_collection.create_index([('title', 'text'), ('description', 'text')])

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