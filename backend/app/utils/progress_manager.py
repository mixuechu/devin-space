import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

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
        os.makedirs(self.intermediate_dir, exist_ok=True)
    
    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        if not os.path.exists(self.progress_file):
            return {
                'current_stage': None,
                'completed_stages': [],
                'last_updated': None,
                'processed_count': 0,
                'total_count': 0
            }
        
        with open(self.progress_file, 'r') as f:
            return json.load(f)
    
    def update_progress(self, stage: str, processed_count: int = 0, total_count: int = 0) -> None:
        """更新进度信息"""
        progress = self.get_progress()
        
        if stage not in progress['completed_stages']:
            progress['current_stage'] = stage
            progress['processed_count'] = processed_count
            progress['total_count'] = total_count
            progress['last_updated'] = datetime.now().isoformat()
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
    
    def complete_stage(self, stage: str) -> None:
        """标记某个阶段为完成"""
        progress = self.get_progress()
        
        if stage not in progress['completed_stages']:
            progress['completed_stages'].append(stage)
            progress['current_stage'] = None
            progress['last_updated'] = datetime.now().isoformat()
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
    
    def save_intermediate_result(self, stage: str, data: Any) -> None:
        """保存中间结果"""
        file_path = os.path.join(self.intermediate_dir, f"{stage}_result.json")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def load_intermediate_result(self, stage: str) -> Optional[Any]:
        """加载中间结果"""
        file_path = os.path.join(self.intermediate_dir, f"{stage}_result.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def reset_progress(self) -> None:
        """重置所有进度"""
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        
        # 清除所有中间结果
        for file in os.listdir(self.intermediate_dir):
            if file.endswith('_result.json'):
                os.remove(os.path.join(self.intermediate_dir, file)) 