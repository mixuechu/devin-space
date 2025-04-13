import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import time
import os

from app.models.server import MCPServer, ServerMetrics
from app.utils.progress_manager import ProgressManager

class DataProcessor:
    """
    Processes raw MCP server data to extract metrics and features.
    """
    
    def __init__(self, data_path: str = ""):
        """
        Initialize the data processor.
        
        Args:
            data_path: Path to the raw MCP server data JSON file.
        """
        self.data_path = data_path
        self.raw_data = None
        self.processed_data = None
        
        # 初始化进度管理器
        data_dir = os.path.dirname(data_path) if data_path else "data"
        self.progress_manager = ProgressManager(data_dir)
        
    def load_data(self, data_path: str = "") -> List[Dict[str, Any]]:
        """
        Load raw MCP server data from a JSON file.
        """
        print("\n=== 开始加载数据文件 ===")
        start_time = time.time()
        
        # 检查是否已完成数据加载
        if 'data_loading' in self.progress_manager.get_progress()['completed_stages']:
            print("发现已加载的数据，正在恢复...")
            self.raw_data = self.progress_manager.load_intermediate_result('data_loading')
            print(f"成功恢复已加载的数据，共 {len(self.raw_data)} 条记录")
            return self.raw_data
        
        if data_path:
            self.data_path = data_path
        
        if not self.data_path:
            raise ValueError("Data path not provided.")
        
        try:
            print(f"正在读取文件: {self.data_path}")
            with open(self.data_path, 'r', encoding='utf-8') as f:
                print("文件打开成功，正在解析JSON...")
                self.raw_data = json.load(f)
                
            print(f"JSON解析完成，共读取 {len(self.raw_data)} 条数据")
            print(f"数据加载总耗时: {time.time() - start_time:.2f}秒")
            
            # 保存加载结果
            self.progress_manager.save_intermediate_result('data_loading', self.raw_data)
            self.progress_manager.complete_stage('data_loading')
            
        except Exception as e:
            print(f"数据加载出错: {str(e)}")
            raise
        
        return self.raw_data
    
    def process_data(self) -> List[ServerMetrics]:
        """
        Process raw MCP server data to extract metrics and features.
        """
        if not self.raw_data:
            raise ValueError("Raw data not loaded. Call load_data() first.")
        
        progress = self.progress_manager.get_progress()
        
        # 检查是否已完成所有处理
        if 'metrics_calculation' in progress['completed_stages']:
            print("\n=== 发现已处理完成的数据，正在恢复... ===")
            self.processed_data = [
                ServerMetrics(**item) 
                for item in self.progress_manager.load_intermediate_result('metrics_calculation')
            ]
            return self.processed_data
        
        print("\n=== 开始处理数据 ===")
        start_time = time.time()
        processed_count = 0
        total = len(self.raw_data)
        processed_servers = []
        
        # 恢复之前的处理进度
        if progress['current_stage'] in ['basic_processing', 'feature_extraction']:
            processed_servers = [
                ServerMetrics(**item) 
                for item in self.progress_manager.load_intermediate_result(progress['current_stage'])
            ]
            processed_count = len(processed_servers)
            print(f"恢复之前的处理进度，已处理 {processed_count} 条记录")
        
        for server_data in self.raw_data[processed_count:]:
            try:
                # 基础处理
                server = MCPServer(
                    id=server_data["id"],
                    type=server_data["type"],
                    title=server_data["title"],
                    author=server_data["author"],
                    description=server_data["description"],
                    tags=server_data["tags"],
                    github_url=server_data.get("github_url"),
                    page_url=server_data.get("page_url"),
                    page=server_data["page"],
                    timestamp=datetime.fromisoformat(server_data["timestamp"].replace('Z', '+00:00')),
                    content=server_data.get("content", ""),
                    detailed_content=server_data.get("detailed_content", "")
                )
                
                # 特征提取
                word_count = len(server.detailed_content.split())
                documentation_length = len(server.detailed_content)
                feature_count = server.detailed_content.count('\n-') + server.detailed_content.count('\n•')
                tool_count = server.detailed_content.lower().count('tool')
                has_github = bool(server.github_url)
                has_faq = 'faq' in server.content.lower() or 'frequently asked' in server.content.lower()
                
                # 生成特征向量
                feature_vector = [
                    word_count / 1000,  # Normalize word count
                    documentation_length / 10000,  # Normalize doc length
                    feature_count,
                    tool_count,
                    1 if has_github else 0,
                    1 if has_faq else 0
                ]
                
                # 创建指标对象
                metrics = ServerMetrics(
                    server_id=server.id,
                    title=server.title,
                    author=server.author,
                    description=server.description,
                    tags=server.tags,
                    word_count=word_count,
                    documentation_length=documentation_length,
                    feature_count=feature_count,
                    tool_count=tool_count,
                    has_github=has_github,
                    has_faq=has_faq,
                    feature_vector=feature_vector,
                    raw_data=server_data
                )
                
                processed_servers.append(metrics)
                processed_count += 1
                
                # 更新进度
                if processed_count % 100 == 0:
                    elapsed = time.time() - start_time
                    speed = processed_count / elapsed
                    remaining = (total - processed_count) / speed if speed > 0 else 0
                    print(f"\n当前进度:")
                    print(f"已处理: {processed_count}/{total} ({processed_count/total*100:.1f}%)")
                    print(f"处理速度: {speed:.1f} 条/秒")
                    print(f"预计剩余时间: {remaining/60:.1f} 分钟")
                    
                    # 保存中间结果
                    self.progress_manager.save_intermediate_result('basic_processing', 
                        [server.dict() for server in processed_servers])
                    self.progress_manager.update_progress('basic_processing', 
                        processed_count, total)
                
            except Exception as e:
                print(f"\n处理数据出错 {server_data.get('id', 'unknown')}: {str(e)}")
                continue
        
        print(f"\n数据处理完成，总耗时: {time.time() - start_time:.2f}秒")
        
        # 保存最终结果
        self.processed_data = processed_servers
        self.progress_manager.save_intermediate_result('metrics_calculation', 
            [server.dict() for server in processed_servers])
        self.progress_manager.complete_stage('metrics_calculation')
        
        return processed_servers
    
    def save_processed_data(self, output_path: str) -> None:
        """
        Save processed data to a JSON file.
        """
        if not self.processed_data:
            raise ValueError("No processed data available. Call process_data() first.")
        
        processed_data_dict = [server.dict() for server in self.processed_data]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data_dict, f, indent=2, default=str)
        
        print(f"\n处理后的数据已保存到: {output_path}")
    
    def get_dataframe(self) -> pd.DataFrame:
        """
        Convert processed data to a pandas DataFrame.
        """
        if not self.processed_data:
            raise ValueError("No processed data available. Call process_data() first.")
        
        processed_data_dict = [
            {
                "server_id": server.server_id,
                "title": server.title,
                "author": server.author,
                "tags": ", ".join(server.tags),
                "word_count": server.word_count,
                "documentation_length": server.documentation_length,
                "feature_count": server.feature_count,
                "tool_count": server.tool_count,
                "has_github": server.has_github,
                "has_faq": server.has_faq
            }
            for server in self.processed_data
        ]
        
        return pd.DataFrame(processed_data_dict)
