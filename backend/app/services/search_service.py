from typing import List, Dict, Any, Optional
import pandas as pd
from fuzzywuzzy import fuzz
from app.models.cluster import ClusterSummary
from app.core.database import get_all_clusters

class SearchService:
    def __init__(self):
        self._clusters_df: Optional[pd.DataFrame] = None
        self._search_index: Dict[str, List[int]] = {}
        
    def build_index(self, clusters: List[Dict[str, Any]]):
        """构建搜索索引"""
        try:
            # 从数据库获取所有集群信息
            db_clusters = get_all_clusters()
            print("[Search] Retrieved clusters from database")  # Debug log
            
            # 将集群数据转换为DataFrame以便于处理
            clusters_data = []
            for cluster in db_clusters:
                cluster_data = {
                    'cluster_id': cluster.get('cluster_id'),
                    'cluster_name': cluster.get('cluster_name', ''),
                    'description': cluster.get('description', ''),
                    'common_tags': ' '.join(cluster.get('common_tags', [])),
                    'server_count': cluster.get('size', 0),
                    'raw_data': cluster
                }
                clusters_data.append(cluster_data)
            
            if not clusters_data:
                print("[Search] No clusters data available")  # Debug log
                return
            
            self._clusters_df = pd.DataFrame(clusters_data)
            
            # 验证DataFrame的列
            print("[Search] Building search index with columns:", self._clusters_df.columns.tolist())  # Debug log
            
            # 构建搜索索引
            for idx, row in self._clusters_df.iterrows():
                # 为每个字段创建搜索索引
                if pd.notna(row['cluster_name']):  # 检查是否为空
                    self._add_to_index(str(row['cluster_name']).lower(), idx)
                if pd.notna(row['description']):  # 检查是否为空
                    self._add_to_index(str(row['description']).lower(), idx)
                if pd.notna(row['common_tags']):  # 检查是否为空
                    for tag in str(row['common_tags']).split():
                        self._add_to_index(tag.lower(), idx)
            
            print(f"[Search] Index built successfully with {len(self._search_index)} terms")  # Debug log
            
        except Exception as e:
            print(f"[Search] Error building search index: {str(e)}")  # Debug log
            raise
    
    def _add_to_index(self, text: str, idx: int):
        """将文本添加到搜索索引中"""
        words = text.split()
        for word in words:
            if word not in self._search_index:
                self._search_index[word] = []
            if idx not in self._search_index[word]:
                self._search_index[word].append(idx)
    
    def search(self, query: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """搜索集群"""
        if self._clusters_df is None:
            return {
                'items': [],
                'total': 0,
                'page': page,
                'page_size': page_size
            }

        if not query:
            # 如果没有查询词，返回按服务器数量排序的结果
            sorted_clusters = self._clusters_df.sort_values('server_count', ascending=False)
            total = len(sorted_clusters)
            page_data = sorted_clusters.iloc[(page-1)*page_size:page*page_size]
            return {
                'items': [row['raw_data'] for _, row in page_data.iterrows()],
                'total': total,
                'page': page,
                'page_size': page_size
            }
        
        # 将查询词转换为小写并分词
        query_words = query.lower().split()
        
        # 收集所有匹配的索引
        matched_indices = set()
        for word in query_words:
            # 对每个查询词进行模糊匹配
            for index_word, indices in self._search_index.items():
                if fuzz.partial_ratio(word, index_word) > 80:  # 80%的相似度阈值
                    matched_indices.update(indices)
        
        if not matched_indices:
            return {
                'items': [],
                'total': 0,
                'page': page,
                'page_size': page_size
            }
        
        # 获取匹配的行
        matched_clusters = self._clusters_df.iloc[list(matched_indices)]
        
        # 计算相关性得分
        scores = []
        for _, row in matched_clusters.iterrows():
            score = 0
            searchable_text = f"{row['cluster_name']} {row['description']} {row['common_tags']}".lower()
            for word in query_words:
                score += fuzz.partial_ratio(word, searchable_text)
            scores.append(score)
        
        matched_clusters['search_score'] = scores
        
        # 按相关性得分和服务器数量排序
        sorted_clusters = matched_clusters.sort_values(
            ['search_score', 'server_count'], 
            ascending=[False, False]
        )
        
        # 分页
        total = len(sorted_clusters)
        page_data = sorted_clusters.iloc[(page-1)*page_size:page*page_size]
        
        # 确保返回的数据包含正确的字段
        items = []
        for _, row in page_data.iterrows():
            raw_data = row['raw_data']
            if isinstance(raw_data, dict):
                # 确保 cluster_name 字段存在
                if 'cluster_name' not in raw_data:
                    raw_data['cluster_name'] = row['cluster_name']
                items.append(raw_data)
            else:
                items.append({
                    'cluster_id': row['cluster_id'],
                    'cluster_name': row['cluster_name'],
                    'description': row['description'],
                    'common_tags': row['common_tags'].split(),
                    'server_count': row['server_count']
                })
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }

# 创建全局搜索服务实例
search_service = SearchService() 