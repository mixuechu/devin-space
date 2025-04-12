import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from app.models.server import MCPServer, ServerMetrics

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
    
    def load_data(self, data_path: str = "") -> List[Dict[str, Any]]:
        """
        Load raw MCP server data from a JSON file.
        
        Args:
            data_path: Path to the raw MCP server data JSON file.
            
        Returns:
            List of dictionaries containing raw MCP server data.
        """
        if data_path:
            self.data_path = data_path
        
        if not self.data_path:
            raise ValueError("Data path not provided.")
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
        except FileNotFoundError:
            base_path = Path(__file__).parent.parent.parent.parent.parent
            full_path = base_path / self.data_path
            with open(full_path, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
        
        return self.raw_data
    
    def process_data(self) -> List[ServerMetrics]:
        """
        Process raw MCP server data to extract metrics and features.
        
        Returns:
            List of ServerMetrics objects containing processed data.
        """
        if not self.raw_data:
            raise ValueError("Raw data not loaded. Call load_data() first.")
        
        processed_servers = []
        
        for server_data in self.raw_data:
            try:
                try:
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
                except Exception as e:
                    print(f"Error creating MCPServer object for {server_data.get('id', 'unknown')}: {str(e)}")
                    print(f"Server data keys: {server_data.keys()}")
                    continue
                
                word_count = len(server.detailed_content.split())
                documentation_length = len(server.detailed_content)
                
                feature_count = server.detailed_content.count('\n-') + server.detailed_content.count('\n•')
                
                tool_count = server.detailed_content.lower().count('tool')
                
                has_github = bool(server.github_url)
                has_faq = 'faq' in server.content.lower() or 'frequently asked' in server.content.lower()
                
                feature_vector = [
                    word_count / 1000,  # Normalize word count
                    documentation_length / 10000,  # Normalize doc length
                    feature_count,
                    tool_count,
                    1 if has_github else 0,
                    1 if has_faq else 0
                ]
                
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
                
            except Exception as e:
                print(f"Error processing server {server_data.get('id', 'unknown')}: {str(e)}")
        
        self.processed_data = processed_servers
        return processed_servers
    
    def save_processed_data(self, output_path: str) -> None:
        """
        Save processed data to a JSON file.
        
        Args:
            output_path: Path to save the processed data.
        """
        if not self.processed_data:
            raise ValueError("No processed data available. Call process_data() first.")
        
        processed_data_dict = [server.dict() for server in self.processed_data]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data_dict, f, indent=2, default=str)
    
    def get_dataframe(self) -> pd.DataFrame:
        """
        Convert processed data to a pandas DataFrame.
        
        Returns:
            DataFrame containing processed server data.
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
