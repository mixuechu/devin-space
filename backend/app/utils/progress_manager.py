import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProgressManager:
    """管理数据处理进度的类"""
    
    STAGES = [
        'data_loading',
        'basic_processing',
        'feature_extraction',
        'metrics_calculation',
        'clustering',
        'evaluation'
    ]
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.progress_file = os.path.join(data_dir, "processing_progress.json")
        self.intermediate_dir = os.path.join(data_dir, "intermediate")
        try:
            os.makedirs(self.intermediate_dir, exist_ok=True)
            logger.info(f"初始化进度管理器: {self.intermediate_dir}")
        except Exception as e:
            logger.error(f"创建中间结果目录失败: {str(e)}")
            raise
    
    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        try:
            if not os.path.exists(self.progress_file):
                logger.info("进度文件不存在，返回初始状态")
                return {
                    'current_stage': None,
                    'completed_stages': [],
                    'last_updated': None,
                    'processed_count': 0,
                    'total_count': 0
                }
            
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                logger.info(f"已加载进度: {progress['completed_stages']}")
                return progress
        except Exception as e:
            logger.error(f"读取进度文件失败: {str(e)}")
            return {
                'current_stage': None,
                'completed_stages': [],
                'last_updated': None,
                'processed_count': 0,
                'total_count': 0
            }
    
    def update_progress(self, stage: str, processed_count: int = 0, total_count: int = 0) -> None:
        """更新进度信息"""
        try:
            progress = self.get_progress()
            
            if stage not in progress['completed_stages']:
                progress['current_stage'] = stage
                progress['processed_count'] = processed_count
                progress['total_count'] = total_count
                progress['last_updated'] = datetime.now().isoformat()
                
                with open(self.progress_file, 'w') as f:
                    json.dump(progress, f, indent=2)
                logger.info(f"更新进度: {stage} ({processed_count}/{total_count})")
        except Exception as e:
            logger.error(f"更新进度失败: {str(e)}")
    
    def complete_stage(self, stage: str) -> None:
        """标记某个阶段为完成"""
        try:
            progress = self.get_progress()
            
            if stage not in progress['completed_stages']:
                progress['completed_stages'].append(stage)
                progress['current_stage'] = None
                progress['last_updated'] = datetime.now().isoformat()
                
                with open(self.progress_file, 'w') as f:
                    json.dump(progress, f, indent=2)
                logger.info(f"完成阶段: {stage}")
        except Exception as e:
            logger.error(f"标记阶段完成失败: {str(e)}")
    
    def save_intermediate_result(self, stage: str, data: Any) -> None:
        """保存中间结果"""
        try:
            file_path = os.path.join(self.intermediate_dir, f"{stage}_result.json")
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"保存中间结果: {stage}")
        except Exception as e:
            logger.error(f"保存中间结果失败 {stage}: {str(e)}")
            raise
    
    def load_intermediate_result(self, stage: str) -> Optional[Any]:
        """加载中间结果"""
        try:
            file_path = os.path.join(self.intermediate_dir, f"{stage}_result.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"加载中间结果: {stage}")
                return data
            logger.warning(f"中间结果不存在: {stage}")
            return None
        except Exception as e:
            logger.error(f"加载中间结果失败 {stage}: {str(e)}")
            return None
    
    def verify_cache_integrity(self) -> bool:
        """验证缓存完整性"""
        try:
            progress = self.get_progress()
            completed_stages = progress['completed_stages']
            
            for stage in completed_stages:
                file_path = os.path.join(self.intermediate_dir, f"{stage}_result.json")
                if not os.path.exists(file_path):
                    logger.error(f"缓存文件缺失: {stage}")
                    return False
                
                # 验证文件可读性
                try:
                    with open(file_path, 'r') as f:
                        json.load(f)
                except:
                    logger.error(f"缓存文件损坏: {stage}")
                    return False
            
            logger.info("缓存完整性验证通过")
            return True
        except Exception as e:
            logger.error(f"验证缓存完整性失败: {str(e)}")
            return False
    
    def reset_progress(self) -> None:
        """重置所有进度"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
            
            # 清除所有中间结果
            for file in os.listdir(self.intermediate_dir):
                if file.endswith('_result.json'):
                    os.remove(os.path.join(self.intermediate_dir, file))
            logger.info("重置所有进度和缓存")
        except Exception as e:
            logger.error(f"重置进度失败: {str(e)}")
            raise 