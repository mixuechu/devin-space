import os
import shutil
from pymongo import MongoClient
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_mongodb_clusters():
    """清除 MongoDB 中的集群数据"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['server_explorer']
        
        # 删除集群集合
        db.clusters.drop()
        
        # 重新创建索引
        db.clusters.create_index('cluster_id', unique=True)
        db.clusters.create_index('cluster_name')
        
        logger.info("Successfully cleared MongoDB clusters collection and recreated indices")
    except Exception as e:
        logger.error(f"Error clearing MongoDB clusters: {str(e)}")
        raise

def clear_cache_files():
    """清除缓存文件"""
    try:
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 清除中间结果目录
        intermediate_dir = os.path.join(current_dir, 'data', 'intermediate')
        if os.path.exists(intermediate_dir):
            for filename in os.listdir(intermediate_dir):
                if filename.startswith('clustering_') or filename == 'clustering_result.json':
                    file_path = os.path.join(intermediate_dir, filename)
                    os.remove(file_path)
                    logger.info(f"Removed cache file: {file_path}")
        
        logger.info("Successfully cleared cache files")
    except Exception as e:
        logger.error(f"Error clearing cache files: {str(e)}")
        raise

def main():
    """主函数"""
    try:
        logger.info("Starting cleanup process...")
        
        # 清除 MongoDB 集群数据
        clear_mongodb_clusters()
        
        # 清除缓存文件
        clear_cache_files()
        
        logger.info("Cleanup completed successfully!")
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 