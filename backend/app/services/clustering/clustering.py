import numpy as np
from typing import List, Dict, Any
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import pandas as pd

from app.models.server import ServerMetrics

class ClusteringService:
    """
    Service for clustering MCP servers based on their features.
    """
    
    def __init__(self, n_clusters: int = 5):
        """
        Initialize the clustering service.
        
        Args:
            n_clusters: Number of clusters to create.
        """
        self.n_clusters = n_clusters
        self.scaler = StandardScaler()
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        self.pca = PCA(n_components=2)
        self.tsne = TSNE(n_components=2, random_state=42)
        self.cluster_labels = None
        self.cluster_centers = None
        self.visualization_data = None
    
    def extract_feature_matrix(self, servers: List[ServerMetrics]) -> np.ndarray:
        """
        Extract feature matrix from server metrics.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            NumPy array containing feature vectors.
        """
        feature_matrix = np.array([server.feature_vector for server in servers])
        return feature_matrix
    
    def cluster_servers(self, servers: List[ServerMetrics]) -> List[ServerMetrics]:
        """
        Cluster servers based on their features.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            List of ServerMetrics objects with cluster assignments.
        """
        feature_matrix = self.extract_feature_matrix(servers)
        
        scaled_features = self.scaler.fit_transform(feature_matrix)
        
        self.cluster_labels = self.kmeans.fit_predict(scaled_features)
        self.cluster_centers = self.kmeans.cluster_centers_
        
        for i, server in enumerate(servers):
            server.cluster_id = int(self.cluster_labels[i])
        
        return servers
    
    def generate_visualization_data(self, servers: List[ServerMetrics]) -> Dict[str, Any]:
        """
        Generate data for visualizing clusters.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            Dictionary containing visualization data.
        """
        feature_matrix = self.extract_feature_matrix(servers)
        
        scaled_features = self.scaler.fit_transform(feature_matrix)
        
        pca_result = self.pca.fit_transform(scaled_features)
        tsne_result = self.tsne.fit_transform(scaled_features)
        
        visualization_data = {
            "pca": {
                "x": pca_result[:, 0].tolist(),
                "y": pca_result[:, 1].tolist()
            },
            "tsne": {
                "x": tsne_result[:, 0].tolist(),
                "y": tsne_result[:, 1].tolist()
            },
            "clusters": self.cluster_labels.tolist(),
            "server_ids": [server.server_id for server in servers],
            "titles": [server.title for server in servers]
        }
        
        self.visualization_data = visualization_data
        return visualization_data
    
    def get_cluster_summary(self, servers: List[ServerMetrics]) -> List[Dict[str, Any]]:
        """
        Generate summaries for each cluster including metrics and common characteristics
        """
        cluster_summaries = []
        existing_names = set()  # 用于追踪已使用的名称

        for cluster_id, cluster_servers in enumerate(self.clusters):
            if not cluster_servers:
                continue

            # 计算基础指标
            titles = [server.title for server in cluster_servers]
            word_counts = [len(server.title.split()) for server in cluster_servers]
            avg_word_count = sum(word_counts) / len(word_counts)
            
            feature_counts = [len(server.features) for server in cluster_servers]
            avg_feature_count = sum(feature_counts) / len(feature_counts)
            
            tool_counts = [len(server.tools) for server in cluster_servers]
            avg_tool_count = sum(tool_counts) / len(tool_counts)
            
            # 提取共同标签
            tag_counts = {}
            for server in cluster_servers:
                for tag in server.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # 选择出现在至少50%服务器中的标签
            threshold = len(cluster_servers) * 0.5
            common_tags = [tag for tag, count in tag_counts.items() if count >= threshold]

            # 确定集群复杂度
            is_advanced = avg_tool_count > 5 or avg_feature_count > 10
            complexity_prefix = "Advanced" if is_advanced else "Basic"

            # 生成基础名称
            base_name = ""
            if len(titles) > 1:
                # 尝试找到共同前缀
                first_title = titles[0]
                for i in range(len(first_title)):
                    if all(title.startswith(first_title[:i+1]) for title in titles[1:]):
                        common_prefix = first_title[:i+1].strip()
                        if common_prefix:
                            base_name = common_prefix
                    else:
                        break

            # 如果没有找到有效的共同前缀，使用最常见的词
            if not base_name:
                words = []
                for title in titles:
                    words.extend(title.lower().split())
                word_counts = {}
                for word in words:
                    if len(word) > 2:  # 跳过短词
                        word_counts[word] = word_counts.get(word, 0) + 1
                most_common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:2]
                if most_common_words:
                    base_name = ' '.join(word.title() for word, _ in most_common_words)

            # 如果还是没有名称，使用第一个标题
            if not base_name:
                base_name = titles[0][:30]

            # 生成完整的集群名称
            cluster_name = f"{complexity_prefix} {base_name} Services"

            # 处理重名情况
            original_name = cluster_name
            counter = 1
            while cluster_name in existing_names:
                # 尝试添加统计信息
                if counter == 1:
                    cluster_name = f"{original_name} ({int(avg_tool_count)} Tools)"
                elif counter == 2:
                    cluster_name = f"{original_name} ({int(avg_feature_count)} Features)"
                else:
                    cluster_name = f"{original_name} (Group {cluster_id})"
                counter += 1

            existing_names.add(cluster_name)

            summary = {
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "size": len(cluster_servers),
                "servers": [{"id": server.server_id, "title": server.title} for server in cluster_servers],
                "avg_word_count": avg_word_count,
                "avg_feature_count": avg_feature_count,
                "avg_tool_count": avg_tool_count,
                "common_tags": common_tags
            }
            
            cluster_summaries.append(summary)
        
        return cluster_summaries
    
    def get_similar_servers(self, server_id: str, servers: List[ServerMetrics], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Find similar servers to a given server.
        
        Args:
            server_id: ID of the server to find similar servers for.
            servers: List of ServerMetrics objects.
            top_n: Number of similar servers to return.
            
        Returns:
            List of dictionaries containing similar servers.
        """
        target_server = None
        for server in servers:
            if server.server_id == server_id:
                target_server = server
                break
        
        if not target_server:
            raise ValueError(f"Server with ID {server_id} not found.")
        
        cluster_servers = [server for server in servers if server.cluster_id == target_server.cluster_id and server.server_id != server_id]
        
        if not cluster_servers:
            return []
        
        target_vector = np.array(target_server.feature_vector)
        
        distances = []
        for server in cluster_servers:
            server_vector = np.array(server.feature_vector)
            distance = np.linalg.norm(target_vector - server_vector)
            distances.append((server, distance))
        
        distances.sort(key=lambda x: x[1])
        
        similar_servers = []
        for server, distance in distances[:top_n]:
            similar_servers.append({
                "id": server.server_id,
                "title": server.title,
                "similarity_score": 1.0 / (1.0 + distance),  # Convert distance to similarity score
                "distance": distance
            })
        
        return similar_servers
