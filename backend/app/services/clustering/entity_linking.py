import numpy as np
from typing import List, Dict, Any, Tuple
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from fuzzywuzzy import fuzz

from app.models.server import ServerMetrics

class EntityLinkingService:
    """
    Service for clustering MCP servers based on entity linking.
    This groups related servers like "binance server", "binance mcp", "binance helper" together.
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize the entity linking service.
        
        Args:
            similarity_threshold: Threshold for considering two servers as related.
        """
        self.similarity_threshold = similarity_threshold
        self.clusters = {}  # Maps server_id to cluster_id
        self.cluster_data = {}  # Stores cluster information
        self.next_cluster_id = 0
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english'
        )
        
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for entity linking.
        
        Args:
            text: Text to preprocess.
            
        Returns:
            Preprocessed text.
        """
        text = text.lower()
        
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_entity_name(self, title: str) -> str:
        """
        Extract the main entity name from a server title.
        
        Args:
            title: Server title.
            
        Returns:
            Main entity name.
        """
        common_suffixes = [
            "server", "mcp", "helper", "tools", "api", "service", 
            "platform", "framework", "library", "sdk", "client"
        ]
        
        title_lower = title.lower()
        
        for suffix in common_suffixes:
            if title_lower.endswith(f" {suffix}"):
                return title[:-len(suffix)-1].strip()
        
        words = title.split()
        if len(words) > 1:
            return words[0]
        
        return title
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two server titles.
        
        Args:
            title1: First server title.
            title2: Second server title.
            
        Returns:
            Similarity score between 0 and 1.
        """
        entity1 = self.extract_entity_name(title1)
        entity2 = self.extract_entity_name(title2)
        
        ratio = fuzz.ratio(entity1.lower(), entity2.lower()) / 100.0
        
        if ratio > 0.8:
            if title1.lower() in title2.lower() or title2.lower() in title1.lower():
                return 0.95
        
        return ratio
    
    def calculate_tag_similarity(self, tags1: List[str], tags2: List[str]) -> float:
        """
        Calculate similarity between two sets of tags.
        
        Args:
            tags1: First set of tags.
            tags2: Second set of tags.
            
        Returns:
            Similarity score between 0 and 1.
        """
        clean_tags1 = [tag.lower().replace('#', '').strip() for tag in tags1]
        clean_tags2 = [tag.lower().replace('#', '').strip() for tag in tags2]
        
        intersection = set(clean_tags1).intersection(set(clean_tags2))
        union = set(clean_tags1).union(set(clean_tags2))
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)
    
    def calculate_description_similarity(self, desc1: str, desc2: str) -> float:
        """
        Calculate similarity between two server descriptions.
        
        Args:
            desc1: First server description.
            desc2: Second server description.
            
        Returns:
            Similarity score between 0 and 1.
        """
        clean_desc1 = self.preprocess_text(desc1)
        clean_desc2 = self.preprocess_text(desc2)
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform([clean_desc1, clean_desc2])
            similarity = cosine_similarity(tfidf_matrix)[0][1]
            return float(similarity)
        except:
            words1 = set(clean_desc1.split())
            words2 = set(clean_desc2.split())
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            if not union:
                return 0.0
                
            return len(intersection) / len(union)
    
    def calculate_server_similarity(self, server1: ServerMetrics, server2: ServerMetrics) -> float:
        """
        Calculate overall similarity between two servers.
        
        Args:
            server1: First server.
            server2: Second server.
            
        Returns:
            Overall similarity score between 0 and 1.
        """
        title_sim = self.calculate_title_similarity(server1.title, server2.title)
        tag_sim = self.calculate_tag_similarity(server1.tags, server2.tags)
        desc_sim = self.calculate_description_similarity(server1.description, server2.description)
        
        weights = {
            'title': 0.6,
            'tags': 0.2,
            'description': 0.2
        }
        
        overall_sim = (
            weights['title'] * title_sim +
            weights['tags'] * tag_sim +
            weights['description'] * desc_sim
        )
        
        return overall_sim
    
    def cluster_servers(self, servers: List[ServerMetrics]) -> List[ServerMetrics]:
        """
        Cluster servers based on entity linking.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            List of ServerMetrics objects with cluster assignments.
        """
        self.clusters = {}
        self.cluster_data = {}
        self.next_cluster_id = 0
        
        entity_groups = defaultdict(list)
        
        for server in servers:
            entity_name = self.extract_entity_name(server.title).lower()
            entity_groups[entity_name].append(server)
        
        for entity_name, group_servers in entity_groups.items():
            if len(group_servers) > 0:
                cluster_id = self.next_cluster_id
                self.next_cluster_id += 1
                
                for server in group_servers:
                    self.clusters[server.server_id] = cluster_id
                
                self.cluster_data[cluster_id] = {
                    'entity_name': entity_name,
                    'servers': [s.server_id for s in group_servers]
                }
        
        merged = True
        while merged:
            merged = False
            cluster_ids = list(self.cluster_data.keys())
            
            for i in range(len(cluster_ids)):
                if merged:
                    break
                    
                for j in range(i + 1, len(cluster_ids)):
                    cluster1 = cluster_ids[i]
                    cluster2 = cluster_ids[j]
                    
                    if cluster1 not in self.cluster_data or cluster2 not in self.cluster_data:
                        continue
                    
                    server1_id = self.cluster_data[cluster1]['servers'][0]
                    server2_id = self.cluster_data[cluster2]['servers'][0]
                    
                    server1 = next((s for s in servers if s.server_id == server1_id), None)
                    server2 = next((s for s in servers if s.server_id == server2_id), None)
                    
                    if server1 and server2:
                        similarity = self.calculate_server_similarity(server1, server2)
                        
                        if similarity >= self.similarity_threshold:
                            for server_id in self.cluster_data[cluster2]['servers']:
                                self.clusters[server_id] = cluster1
                            
                            self.cluster_data[cluster1]['servers'].extend(self.cluster_data[cluster2]['servers'])
                            del self.cluster_data[cluster2]
                            
                            merged = True
                            break
        
        for server in servers:
            cluster_id = self.clusters.get(server.server_id)
            if cluster_id is not None:
                server.cluster_id = cluster_id
            else:
                server.cluster_id = self.next_cluster_id
                self.clusters[server.server_id] = self.next_cluster_id
                
                self.cluster_data[self.next_cluster_id] = {
                    'entity_name': self.extract_entity_name(server.title).lower(),
                    'servers': [server.server_id]
                }
                
                self.next_cluster_id += 1
        
        return servers
    
    def generate_visualization_data(self, servers: List[ServerMetrics]) -> Dict[str, Any]:
        """
        Generate data for visualizing entity clusters.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            Dictionary containing visualization data.
        """
        
        if any(server.cluster_id is None for server in servers):
            self.cluster_servers(servers)
        
        cluster_centers = {}
        for cluster_id in set(server.cluster_id for server in servers if server.cluster_id is not None):
            cluster_servers = [s for s in servers if s.cluster_id == cluster_id]
            if cluster_servers:
                feature_vectors = np.array([s.feature_vector for s in cluster_servers])
                cluster_centers[cluster_id] = np.mean(feature_vectors, axis=0)
        
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
            
            server_vector = np.array(server.feature_vector)
            distance = np.linalg.norm(server_vector - center)
            
            cluster_servers = [s for s in servers if s.cluster_id == server.cluster_id]
            angle = 2 * np.pi * cluster_servers.index(server) / max(1, len(cluster_servers))
            
            radius = 0.5 + 0.5 * (1.0 / (1.0 + distance))  # Normalize distance
            x = radius * np.cos(angle) + 2 * server.cluster_id  # Separate clusters horizontally
            y = radius * np.sin(angle)
            
            x_coords.append(float(x))
            y_coords.append(float(y))
            cluster_ids.append(int(server.cluster_id))
            server_ids.append(server.server_id)
            titles.append(server.title)
        
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
    
    def get_cluster_summary(self, servers: List[ServerMetrics]) -> List[Dict[str, Any]]:
        """
        Generate summary information for each entity cluster.
        
        Args:
            servers: List of ServerMetrics objects.
            
        Returns:
            List of dictionaries containing cluster summaries.
        """
        if any(server.cluster_id is None for server in servers):
            self.cluster_servers(servers)
        
        cluster_summaries = []
        
        clusters = defaultdict(list)
        for server in servers:
            if server.cluster_id is not None:
                clusters[server.cluster_id].append(server)
        
        for cluster_id, cluster_servers in clusters.items():
            if not cluster_servers:
                continue
            
            entity_name = self.extract_entity_name(cluster_servers[0].title)
            
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
                "entity_name": entity_name,
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
        Find similar servers to a given server based on entity linking.
        
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
        
        if any(server.cluster_id is None for server in servers):
            self.cluster_servers(servers)
        
        cluster_servers = [
            server for server in servers 
            if server.cluster_id == target_server.cluster_id and server.server_id != server_id
        ]
        
        if not cluster_servers:
            similarities = []
            for server in servers:
                if server.server_id != server_id:
                    similarity = self.calculate_server_similarity(target_server, server)
                    similarities.append((server, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            similar_servers = [
                {
                    "id": server.server_id,
                    "title": server.title,
                    "similarity_score": similarity,
                    "same_cluster": False
                }
                for server, similarity in similarities[:top_n]
            ]
        else:
            similarities = []
            for server in cluster_servers:
                similarity = self.calculate_server_similarity(target_server, server)
                similarities.append((server, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            similar_servers = [
                {
                    "id": server.server_id,
                    "title": server.title,
                    "similarity_score": similarity,
                    "same_cluster": True
                }
                for server, similarity in similarities[:top_n]
            ]
        
        return similar_servers
