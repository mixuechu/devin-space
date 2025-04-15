from typing import Optional
from app.models.cluster import ClusteringData, ClusterSummary, Server
import random

def _generate_test_data() -> ClusteringData:
    """生成测试数据"""
    # 定义一些测试用的标签组
    tag_groups = [
        ["web", "frontend", "react", "javascript"],
        ["backend", "python", "api", "fastapi"],
        ["database", "mysql", "postgresql", "redis"],
        ["devops", "kubernetes", "docker", "ci/cd"],
        ["ml", "tensorflow", "pytorch", "data-science"],
        ["mobile", "ios", "android", "flutter"],
        ["security", "authentication", "encryption", "oauth"],
        ["testing", "unit-test", "integration-test", "qa"]
    ]
    
    # 生成100个测试集群
    clusters = []
    for i in range(1, 101):
        # 随机选择一个标签组
        tag_group = random.choice(tag_groups)
        # 随机选择2-4个标签
        cluster_tags = random.sample(tag_group, random.randint(2, 4))
        
        # 为每个集群生成5-15个服务器
        servers = []
        for j in range(random.randint(5, 15)):
            server_id = f"server-{i}-{j}"
            server = Server(
                id=server_id,
                title=f"Server {server_id}",
                description=f"A {' '.join(cluster_tags)} server for {cluster_tags[0]} applications",
                tags=cluster_tags + [f"v{random.randint(1, 5)}.{random.randint(0, 9)}"],
                cluster_id=i
            )
            servers.append(server)
        
        # 创建集群
        cluster = ClusterSummary(
            cluster_id=i,
            cluster_name=f"{cluster_tags[0].title()} Cluster {i}",
            description=f"A cluster for {' and '.join(cluster_tags)} services",
            common_tags=cluster_tags,
            servers=servers,
            visualization_coords=[random.random(), random.random()]
        )
        clusters.append(cluster)
    
    # 生成可视化数据
    viz_data = [[random.random(), random.random()] for _ in range(len(clusters))]
    
    return ClusteringData(
        visualization_data=viz_data,
        cluster_summaries=clusters
    )

async def get_clustering_data(threshold: float = 0.7) -> Optional[ClusteringData]:
    """
    获取聚类数据
    
    Args:
        threshold: 聚类阈值
        
    Returns:
        ClusteringData 或 None（如果获取失败）
    """
    try:
        # 生成测试数据
        return _generate_test_data()
        
    except Exception as e:
        print(f"Error getting clustering data: {e}")
        return None

__all__ = ['get_clustering_data']
