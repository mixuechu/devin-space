#!/usr/bin/env python3

import os
import shutil
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_intermediate_files():
    """清理所有中间缓存文件"""
    try:
        backend_dir = Path(__file__).parent.parent
        intermediate_dir = backend_dir / 'data' / 'intermediate'
        progress_file = backend_dir / 'data' / 'processing_progress.json'

        # 清理中间文件目录
        if intermediate_dir.exists():
            logger.info(f"清理中间文件目录: {intermediate_dir}")
            # 删除所有中间文件
            for file in intermediate_dir.glob('*.json'):
                logger.info(f"删除文件: {file}")
                file.unlink()
        else:
            logger.info("创建中间文件目录")
            intermediate_dir.mkdir(parents=True, exist_ok=True)
        
        # 删除进度文件
        if progress_file.exists():
            logger.info(f"删除进度文件: {progress_file}")
            progress_file.unlink()
        
        logger.info("中间文件清理完成")
        return True
    except Exception as e:
        logger.error(f"清理中间文件失败: {e}")
        return False

def clean_mongodb():
    """清理MongoDB数据库"""
    try:
        # MongoDB清理命令
        mongo_cmd = """
        use server_explorer;
        db.dropDatabase();
        use server_explorer;
        db.createCollection("clusters");
        db.createCollection("servers");
        db.clusters.createIndex({"cluster_id": 1}, {unique: true});
        db.clusters.createIndex({"cluster_name": 1}, {unique: false});
        db.servers.createIndex({"server_id": 1}, {unique: true});
        db.servers.createIndex({"cluster_id": 1});
        db.servers.updateMany({}, {$unset: {cluster_id: "", cluster_name: ""}});
        """
        
        # 执行MongoDB命令
        logger.info("开始清理MongoDB数据库")
        result = subprocess.run(
            ['docker', 'exec', 'mongodb', 'mongosh', '--eval', mongo_cmd],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("MongoDB数据库清理完成")
            return True
        else:
            logger.error(f"MongoDB清理失败: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"MongoDB清理出错: {e}")
        return False

def restart_backend():
    """重启后端服务"""
    try:
        # 查找并终止现有的后端进程
        logger.info("正在停止后端服务...")
        subprocess.run(['pkill', '-f', 'uvicorn app.main:app'])
        logger.info("后端服务已停止")
        return True
    except Exception as e:
        logger.error(f"停止后端服务失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=== 开始清理所有数据 ===")
    
    # 清理中间文件
    if clean_intermediate_files():
        logger.info("✓ 中间文件清理成功")
    else:
        logger.error("✗ 中间文件清理失败")
    
    # 清理MongoDB
    if clean_mongodb():
        logger.info("✓ MongoDB清理成功")
    else:
        logger.error("✗ MongoDB清理失败")
    
    # 重启后端服务
    if restart_backend():
        logger.info("✓ 后端服务已停止")
    else:
        logger.error("✗ 后端服务停止失败")
    
    logger.info("""
=== 清理完成 ===
请执行以下命令重启后端服务:
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
""")

if __name__ == "__main__":
    main() 