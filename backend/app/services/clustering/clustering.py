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
        Generate summary information for each cluster.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            List of dictionaries containing cluster summaries.
        """
        if self.cluster_labels is None:
            raise ValueError("Clustering has not been performed. Call cluster_servers() first.")
        
        cluster_summaries = []
        
        for cluster_id in range(self.n_clusters):
            cluster_servers = [server for server in servers if server.cluster_id == cluster_id]
            
            if not cluster_servers:
                continue
            
            avg_word_count = np.mean([server.word_count for server in cluster_servers])
            avg_feature_count = np.mean([server.feature_count for server in cluster_servers])
            avg_tool_count = np.mean([server.tool_count for server in cluster_servers])
            
            all_tags = []
            for server in cluster_servers:
                all_tags.extend(server.tags)
            
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            common_tags = [tag for tag, count in common_tags]
            
            summary = {
                "cluster_id": cluster_id,
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
