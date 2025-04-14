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
        
        # 保存向量化器的词汇表
        vectorizer_data = {
            'title_vocabulary': self.title_vectorizer.vocabulary_,
            'title_idf': self.title_vectorizer.idf_.tolist(),
            'desc_vocabulary': self.desc_vectorizer.vocabulary_,
            'desc_idf': self.desc_vectorizer.idf_.tolist()
        }
        self.progress_manager.save_intermediate_result('vectorizers', vectorizer_data)
        
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
        
        # 8. 预先计算并缓存可视化数据和摘要
        print("正在生成并缓存可视化数据...")
        visualization_data = self._generate_visualization_data_internal(servers)
        self.progress_manager.save_intermediate_result('visualization', visualization_data)
        
        print("正在生成并缓存聚类摘要...")
        cluster_summaries = self._get_cluster_summary_internal(servers)
        self.progress_manager.save_intermediate_result('summaries', cluster_summaries)
        
        print(f"聚类完成! 用时: {time.time() - start_time:.2f}秒")
        print(f"共生成 {len(self.cluster_data)} 个聚类")
        
        return servers
    
    def _get_cluster_summary_internal(self, servers: List[ServerMetrics]) -> List[Dict[str, Any]]:
        """内部方法：生成聚类摘要"""
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

    def get_cluster_summary(self, servers: List[ServerMetrics]) -> List[Dict[str, Any]]:
        """获取聚类摘要信息（优先使用缓存）"""
        cached_summaries = self.progress_manager.load_intermediate_result('summaries')
        if cached_summaries:
            print("使用缓存的聚类摘要")
            return cached_summaries
        
        print("生成新的聚类摘要...")
        summaries = self._get_cluster_summary_internal(servers)
        self.progress_manager.save_intermediate_result('summaries', summaries)
        return summaries

    def _generate_visualization_data_internal(self, servers: List[ServerMetrics]) -> Dict[str, Any]:
        """内部方法：生成可视化数据"""
        # 确保所有服务器都已分配聚类
        if any(server.cluster_id is None for server in servers):
            self.cluster_servers(servers)
        
        # 加载或重新拟合向量化器
        vectorizer_data = self.progress_manager.load_intermediate_result('vectorizers')
        if vectorizer_data:
            print("使用缓存的向量化器数据")
            self.title_vectorizer.vocabulary_ = vectorizer_data['title_vocabulary']
            self.title_vectorizer.idf_ = np.array(vectorizer_data['title_idf'])
            self.desc_vectorizer.vocabulary_ = vectorizer_data['desc_vocabulary']
            self.desc_vectorizer.idf_ = np.array(vectorizer_data['desc_idf'])
        else:
            print("拟合新的向量化器...")
            # 预处理所有文本数据并拟合向量化器
            all_titles = [self.preprocess_text(s.title) for s in servers]
            all_descriptions = [self.preprocess_text(s.description) for s in servers]
            self.title_vectorizer.fit(all_titles)
            self.desc_vectorizer.fit(all_descriptions)
            
            # 保存向量化器数据
            vectorizer_data = {
                'title_vocabulary': self.title_vectorizer.vocabulary_,
                'title_idf': self.title_vectorizer.idf_.tolist(),
                'desc_vocabulary': self.desc_vectorizer.vocabulary_,
                'desc_idf': self.desc_vectorizer.idf_.tolist()
            }
            self.progress_manager.save_intermediate_result('vectorizers', vectorizer_data)
        
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

    def generate_visualization_data(self, servers: List[ServerMetrics]) -> Dict[str, Any]:
        """获取可视化数据（优先使用缓存）"""
        cached_visualization = self.progress_manager.load_intermediate_result('visualization')
        if cached_visualization:
            print("使用缓存的可视化数据")
            return cached_visualization
        
        print("生成新的可视化数据...")
        visualization_data = self._generate_visualization_data_internal(servers)
        self.progress_manager.save_intermediate_result('visualization', visualization_data)
        return visualization_data

    def get_similar_servers(self, server_id: str, servers: List[ServerMetrics], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        查找与给定服务器相似的服务器。
        
        Args:
            server_id: 要查找相似服务器的服务器 ID。
            servers: ServerMetrics 对象列表。
            top_n: 要返回的相似服务器数量。
            
        Returns:
            包含相似服务器信息的字典列表。
        """
        # 找到目标服务器
        target_server = next((server for server in servers if server.server_id == server_id), None)
        if not target_server:
            raise ValueError(f"未找到 ID 为 {server_id} 的服务器。")

        # 确保所有服务器都已分配聚类
        if any(server.cluster_id is None for server in servers):
            self.cluster_servers(servers)

        # 加载或重新拟合向量化器
        vectorizer_data = self.progress_manager.load_intermediate_result('vectorizers')
        if vectorizer_data:
            print("使用缓存的向量化器数据")
            self.title_vectorizer.vocabulary_ = vectorizer_data['title_vocabulary']
            self.title_vectorizer.idf_ = np.array(vectorizer_data['title_idf'])
            self.desc_vectorizer.vocabulary_ = vectorizer_data['desc_vocabulary']
            self.desc_vectorizer.idf_ = np.array(vectorizer_data['desc_idf'])
        else:
            print("拟合新的向量化器...")
            # 预处理所有文本数据并拟合向量化器
            all_titles = [self.preprocess_text(s.title) for s in servers]
            all_descriptions = [self.preprocess_text(s.description) for s in servers]
            self.title_vectorizer.fit(all_titles)
            self.desc_vectorizer.fit(all_descriptions)
            
            # 保存向量化器数据
            vectorizer_data = {
                'title_vocabulary': self.title_vectorizer.vocabulary_,
                'title_idf': self.title_vectorizer.idf_.tolist(),
                'desc_vocabulary': self.desc_vectorizer.vocabulary_,
                'desc_idf': self.desc_vectorizer.idf_.tolist()
            }
            self.progress_manager.save_intermediate_result('vectorizers', vectorizer_data)

        # 获取同一聚类中的其他服务器
        cluster_servers = [
            server for server in servers 
            if server.cluster_id == target_server.cluster_id and server.server_id != server_id
        ]

        # 如果没有同聚类的服务器，则从所有服务器中查找相似的
        if not cluster_servers:
            # 准备目标服务器的文本
            target_title = self.preprocess_text(target_server.title)
            target_desc = self.preprocess_text(target_server.description)

            # 计算与所有其他服务器的相似度
            similarities = []
            for server in servers:
                if server.server_id != server_id:
                    server_title = self.preprocess_text(server.title)
                    server_desc = self.preprocess_text(server.description)

                    # 计算标题和描述的相似度
                    title_vectors = self.title_vectorizer.transform([target_title, server_title])
                    desc_vectors = self.desc_vectorizer.transform([target_desc, server_desc])

                    title_similarity = cosine_similarity(title_vectors)[0][1]
                    desc_similarity = cosine_similarity(desc_vectors)[0][1]

                    # 综合相似度分数
                    similarity = 0.6 * title_similarity + 0.4 * desc_similarity
                    similarities.append((server, similarity))

            # 按相似度排序并返回前 top_n 个
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [
                {
                    "server_id": server.server_id,
                    "title": server.title,
                    "description": server.description,
                    "similarity_score": float(similarity)
                }
                for server, similarity in similarities[:top_n]
            ]
        else:
            # 如果有同聚类的服务器，优先从同聚类中查找
            target_title = self.preprocess_text(target_server.title)
            target_desc = self.preprocess_text(target_server.description)

            similarities = []
            for server in cluster_servers:
                server_title = self.preprocess_text(server.title)
                server_desc = self.preprocess_text(server.description)

                title_vectors = self.title_vectorizer.transform([target_title, server_title])
                desc_vectors = self.desc_vectorizer.transform([target_desc, server_desc])

                title_similarity = cosine_similarity(title_vectors)[0][1]
                desc_similarity = cosine_similarity(desc_vectors)[0][1]

                similarity = 0.6 * title_similarity + 0.4 * desc_similarity
                similarities.append((server, similarity))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return [
                {
                    "server_id": server.server_id,
                    "title": server.title,
                    "description": server.description,
                    "similarity_score": float(similarity)
                }
                for server, similarity in similarities[:top_n]
            ] 