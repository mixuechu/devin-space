import numpy as np
from typing import List, Dict, Any, Tuple
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from fuzzywuzzy import fuzz
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from app.models.server import ServerMetrics
from app.utils.progress_manager import ProgressManager

class OptimizedClusteringService:
    """
    优化后的服务器聚类服务
    使用更高效的算法和并行处理
    """
    
    def __init__(self, data_dir: str, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.clusters = {}
        self.cluster_data = {}
        self.next_cluster_id = 0
        self.progress_manager = ProgressManager(data_dir)
        
        # 向量化器
        self.title_vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english'
        )
        
        self.desc_vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english',
            max_features=1000  # 限制特征数量
        )
    
    @lru_cache(maxsize=1000)
    def preprocess_text(self, text: str) -> str:
        """文本预处理，使用缓存避免重复处理"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()
    
    @lru_cache(maxsize=1000)
    def extract_entity_name(self, title: str) -> str:
        """提取实体名称，使用缓存避免重复处理"""
        common_suffixes = [
            "server", "mcp", "helper", "tools", "api", "service", 
            "platform", "framework", "library", "sdk", "client"
        ]
        
        title_lower = title.lower()
        
        for suffix in common_suffixes:
            if title_lower.endswith(f" {suffix}"):
                return title[:-len(suffix)-1].strip()
        
        words = title.split()
        return words[0] if len(words) > 1 else title
    
    def calculate_batch_similarities(self, 
                                  servers: List[ServerMetrics], 
                                  batch_start: int,
                                  batch_size: int) -> Dict[Tuple[str, str], float]:
        """批量计算相似度"""
        try:
            batch_end = min(batch_start + batch_size, len(servers))
            batch = servers[batch_start:batch_end]
            
            # 准备批次数据
            titles = [self.preprocess_text(server.title) for server in batch]
            descriptions = [self.preprocess_text(server.description) for server in batch]
            
            # 计算向量
            title_vectors = self.title_vectorizer.transform(titles)
            desc_vectors = self.desc_vectorizer.transform(descriptions)
            
            # 计算相似度矩阵
            title_similarities = cosine_similarity(title_vectors)
            desc_similarities = cosine_similarity(desc_vectors)
            
            # 合并结果
            results = {}
            for i, server1 in enumerate(batch):
                for j, server2 in enumerate(servers[batch_start:batch_end]):
                    if server1.server_id != server2.server_id:
                        sim_score = (
                            0.6 * title_similarities[i][j] +
                            0.4 * desc_similarities[i][j]
                        )
                        if sim_score >= self.similarity_threshold:
                            results[(server1.server_id, server2.server_id)] = sim_score
            
            return results
        except Exception as e:
            print(f"计算批次相似度时出错: {str(e)}")
            return {}
    
    def cluster_servers(self, servers: List[ServerMetrics]) -> List[ServerMetrics]:
        """
        优化后的聚类算法
        使用批处理和并行计算
        """
        print("\n=== 开始服务器聚类 ===")
        start_time = time.time()
        
        # 检查是否有缓存的聚类结果
        cached_results = self.progress_manager.load_intermediate_result('clustering')
        if cached_results:
            print("发现缓存的聚类结果，正在恢复...")
            self.clusters = cached_results['clusters']
            self.cluster_data = cached_results['cluster_data']
            self.next_cluster_id = cached_results['next_cluster_id']
            
            # 更新服务器的聚类ID
            for server in servers:
                server.cluster_id = self.clusters.get(server.server_id)
            
            print(f"已恢复 {len(self.cluster_data)} 个聚类")
            return servers
        
        # 1. 预处理
        print("正在预处理数据...")
        titles = [self.preprocess_text(server.title) for server in servers]
        descriptions = [self.preprocess_text(server.description) for server in servers]
        
        # 2. 拟合向量化器
        print("正在拟合文本向量化器...")
        self.title_vectorizer.fit(titles)
        self.desc_vectorizer.fit(descriptions)
        
        # 3. 初始化聚类
        print("正在初始化聚类...")
        title_vectors = self.title_vectorizer.transform(titles)
        initial_similarities = cosine_similarity(title_vectors)
        
        # 4. 快速初始聚类
        print("执行快速初始聚类...")
        clusters_map = {}
        for i in range(len(servers)):
            if i % 100 == 0:
                print(f"处理进度: {i}/{len(servers)}")
            
            if i not in clusters_map:
                clusters_map[i] = self.next_cluster_id
                self.next_cluster_id += 1
            
            # 使用numpy操作加速
            similar_indices = np.where(initial_similarities[i] >= self.similarity_threshold)[0]
            for j in similar_indices:
                if i != j:
                    clusters_map[j] = clusters_map[i]
        
        # 5. 细化聚类
        print("正在细化聚类结果...")
        batch_size = 100
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(0, len(servers), batch_size):
                futures.append(
                    executor.submit(
                        self.calculate_batch_similarities,
                        servers,
                        i,
                        batch_size
                    )
                )
            
            # 收集结果
            for future in as_completed(futures):
                try:
                    similarities = future.result()
                    for (id1, id2), score in similarities.items():
                        idx1 = next(i for i, s in enumerate(servers) if s.server_id == id1)
                        idx2 = next(i for i, s in enumerate(servers) if s.server_id == id2)
                        if score >= self.similarity_threshold:
                            clusters_map[idx2] = clusters_map[idx1]
                except Exception as e:
                    print(f"处理批次时出错: {str(e)}")
                    continue
        
        # 6. 更新结果
        print("正在更新最终结果...")
        for i, server in enumerate(servers):
            cluster_id = clusters_map[i]
            self.clusters[server.server_id] = cluster_id
            server.cluster_id = cluster_id
            
            if cluster_id not in self.cluster_data:
                self.cluster_data[cluster_id] = {
                    'entity_name': self.extract_entity_name(server.title).lower(),
                    'servers': []
                }
            self.cluster_data[cluster_id]['servers'].append(server.server_id)
        
        # 7. 保存结果
        self.progress_manager.save_intermediate_result('clustering', {
            'clusters': self.clusters,
            'cluster_data': self.cluster_data,
            'next_cluster_id': self.next_cluster_id
        })
        self.progress_manager.complete_stage('clustering')
        
        print(f"聚类完成! 用时: {time.time() - start_time:.2f}秒")
        print(f"共生成 {len(self.cluster_data)} 个聚类")
        
        return servers
    
    def get_cluster_summary(self, servers: List[ServerMetrics]) -> List[Dict[str, Any]]:
        """获取聚类摘要信息"""
        summaries = []
        
        for cluster_id, cluster_info in self.cluster_data.items():
            cluster_servers = [
                s for s in servers 
                if s.server_id in cluster_info['servers']
            ]
            
            if not cluster_servers:
                continue
            
            # 计算统计信息
            avg_word_count = np.mean([s.word_count for s in cluster_servers])
            avg_feature_count = np.mean([s.feature_count for s in cluster_servers])
            avg_tool_count = np.mean([s.tool_count for s in cluster_servers])
            
            # 获取共同标签
            all_tags = [tag for s in cluster_servers for tag in s.tags]
            tag_counts = defaultdict(int)
            for tag in all_tags:
                tag_counts[tag.lower()] += 1
            
            common_tags = [
                tag for tag, count in tag_counts.items()
                if count >= len(cluster_servers) * 0.5
            ]
            
            summaries.append({
                'cluster_id': cluster_id,
                'size': len(cluster_servers),
                'entity_name': cluster_info['entity_name'],
                'servers': [
                    {'id': s.server_id, 'title': s.title}
                    for s in cluster_servers
                ],
                'avg_word_count': round(avg_word_count, 2),
                'avg_feature_count': round(avg_feature_count, 2),
                'avg_tool_count': round(avg_tool_count, 2),
                'common_tags': common_tags
            })
        
        return summaries

    def generate_visualization_data(self, servers: List[ServerMetrics]) -> Dict[str, Any]:
        """
        生成聚类可视化数据
        
        Args:
            servers: 服务器列表
            
        Returns:
            包含可视化数据的字典
        """
        # 确保所有服务器都已分配聚类
        if any(server.cluster_id is None for server in servers):
            self.cluster_servers(servers)
        
        # 预处理所有文本数据
        all_titles = [self.preprocess_text(s.title) for s in servers]
        all_descriptions = [self.preprocess_text(s.description) for s in servers]
        
        # 拟合并转换所有数据
        self.title_vectorizer.fit(all_titles)
        self.desc_vectorizer.fit(all_descriptions)
        
        # 计算聚类中心
        cluster_centers = {}
        for cluster_id in set(server.cluster_id for server in servers if server.cluster_id is not None):
            cluster_servers = [s for s in servers if s.cluster_id == cluster_id]
            if cluster_servers:
                # 使用标题和描述的TF-IDF向量作为特征
                titles = [self.preprocess_text(s.title) for s in cluster_servers]
                descriptions = [self.preprocess_text(s.description) for s in cluster_servers]
                
                title_vectors = self.title_vectorizer.transform(titles)
                desc_vectors = self.desc_vectorizer.transform(descriptions)
                
                # 合并特征向量
                title_center = np.mean(title_vectors.toarray(), axis=0)
                desc_center = np.mean(desc_vectors.toarray(), axis=0)
                
                cluster_centers[cluster_id] = {
                    'title': title_center,
                    'description': desc_center
                }
        
        x_coords = []
        y_coords = []
        cluster_ids = []
        server_ids = []
        titles = []
        
        for server in servers:
            if server.cluster_id is None:
                continue
            
            center = cluster_centers.get(server.cluster_id)
            if center is None:
                continue
            
            # 计算服务器与聚类中心的距离
            server_title_vector = self.title_vectorizer.transform([self.preprocess_text(server.title)]).toarray()[0]
            server_desc_vector = self.desc_vectorizer.transform([self.preprocess_text(server.description)]).toarray()[0]
            
            title_distance = np.linalg.norm(server_title_vector - center['title'])
            desc_distance = np.linalg.norm(server_desc_vector - center['description'])
            
            # 综合距离
            distance = 0.6 * title_distance + 0.4 * desc_distance
            
            # 获取同一聚类中的所有服务器
            cluster_servers = [s for s in servers if s.cluster_id == server.cluster_id]
            # 计算服务器在聚类中的角度位置
            angle = 2 * np.pi * cluster_servers.index(server) / max(1, len(cluster_servers))
            
            # 根据距离调整半径
            radius = 0.5 + 0.5 * (1.0 / (1.0 + distance))
            
            # 计算坐标，将不同聚类分散开
            x = radius * np.cos(angle) + 2 * server.cluster_id
            y = radius * np.sin(angle)
            
            x_coords.append(float(x))
            y_coords.append(float(y))
            cluster_ids.append(int(server.cluster_id))
            server_ids.append(server.server_id)
            titles.append(server.title)
        
        # 返回可视化数据
        visualization_data = {
            "pca": {
                "x": x_coords,
                "y": y_coords,
                "clusters": cluster_ids,
                "server_ids": server_ids,
                "titles": titles
            },
            "tsne": {
                "x": x_coords,
                "y": y_coords,
                "clusters": cluster_ids,
                "server_ids": server_ids,
                "titles": titles
            }
        }
        
        return visualization_data 