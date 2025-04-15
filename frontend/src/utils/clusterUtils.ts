import { ClusterSummary } from '../types';

/**
 * 从标签中提取关键词
 */
function extractKeywordsFromTags(tags: string[]): string[] {
    return tags.map(tag => tag.replace(/^#\s*/, ''));
}

/**
 * 从标题中提取关键词
 */
function extractKeywordsFromTitles(titles: string[]): string[] {
    const words = titles.flatMap(title => 
        title.toLowerCase()
            .split(/[\s-]+/)
            .filter(word => word.length > 2)
    );
    
    const wordCounts = new Map<string, number>();
    words.forEach(word => {
        wordCounts.set(word, (wordCounts.get(word) || 0) + 1);
    });
    
    return Array.from(wordCounts.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([word]) => word);
}

/**
 * 生成cluster的描述性名称
 */
function generateBaseName(cluster: ClusterSummary): string {
  // 从common tags中提取关键词
  const tagKeywords = extractKeywordsFromTags(cluster.common_tags);
  
  // 从server titles中提取关键词
  const titleKeywords = extractKeywordsFromTitles(cluster.servers.map(s => s.title));
  
  // 合并关键词并去重
  const allKeywords = [...new Set([...tagKeywords, ...titleKeywords])];
  
  // 根据平均工具数量和特征数量确定cluster的复杂度
  const isAdvanced = cluster.avg_tool_count > 5 || cluster.avg_feature_count > 10;
  const complexityPrefix = isAdvanced ? 'Advanced' : 'Basic';
  
  // 组合关键词（使用前两个）
  const keywordPhrase = allKeywords
    .slice(0, 2)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' & ');
  
  // 生成基础名称
  return `${complexityPrefix} ${keywordPhrase} Services`;
}

/**
 * 为cluster生成唯一的名称
 */
function generateUniqueName(
  baseName: string, 
  cluster: ClusterSummary,
  existingNames: Set<string>,
  allKeywords: string[]
): string {
  // 如果基础名称未被使用，直接返回
  if (!existingNames.has(baseName)) {
    return baseName;
  }

  // 尝试添加第三个关键词
  if (allKeywords.length > 2) {
    const nameWithThirdKeyword = `${baseName.replace(' Services', '')} & ${
      allKeywords[2].charAt(0).toUpperCase() + allKeywords[2].slice(1)
    } Services`;
    if (!existingNames.has(nameWithThirdKeyword)) {
      return nameWithThirdKeyword;
    }
  }

  // 添加统计特征来区分
  const stats = [
    `${Math.round(cluster.avg_tool_count)} Tools`,
    `${Math.round(cluster.avg_feature_count)} Features`,
    `${cluster.size} Servers`
  ];

  for (const stat of stats) {
    const nameWithStat = `${baseName} (${stat})`;
    if (!existingNames.has(nameWithStat)) {
      return nameWithStat;
    }
  }

  // 如果还是重复，添加cluster ID
  return `${baseName} (Group ${cluster.cluster_id})`;
}

/**
 * 为所有cluster生成名称 - 现在直接使用后端提供的名称
 */
export function generateClusterNames(clusters: ClusterSummary[]): ClusterSummary[] {
    // 直接返回原始clusters，因为名称已经由后端生成
    return clusters;
} 