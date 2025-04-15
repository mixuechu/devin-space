from typing import List, Dict, Any, Optional
import pandas as pd
from fuzzywuzzy import fuzz
from app.models.cluster import ClusterSummary

class SearchService:
    def __init__(self):
        self._clusters_df: Optional[pd.DataFrame] = None
        self._search_index: Dict[str, List[int]] = {}
        
    def build_index(self, clusters: List[ClusterSummary]):
        """构建搜索索引"""
        # 将集群数据转换为DataFrame以便于处理
        clusters_data = []
        for cluster in clusters:
            clusters_data.append({
                'cluster_id': cluster.cluster_id,
                'cluster_name': cluster.cluster_name,
                'description': cluster.description or '',
                'common_tags': ' '.join(cluster.common_tags),
                'server_count': len(cluster.servers),
                'raw_data': cluster  # 保存原始数据
            })
        
        self._clusters_df = pd.DataFrame(clusters_data)
        
        # 构建搜索索引
        for idx, row in self._clusters_df.iterrows():
            # 为每个字段创建搜索索引
            self._add_to_index(row['cluster_name'].lower(), idx)
            self._add_to_index(row['description'].lower(), idx)
            for tag in row['common_tags'].split():
                self._add_to_index(tag.lower(), idx)
    
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
        
        return {
            'items': [row['raw_data'] for _, row in page_data.iterrows()],
            'total': total,
            'page': page,
            'page_size': page_size
        }

# 创建全局搜索服务实例
search_service = SearchService() 