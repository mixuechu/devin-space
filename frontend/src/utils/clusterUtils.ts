import { ClusterSummary } from '../types';

/**
 * 从标签列表中提取最常见的关键词
 */
function extractKeywordsFromTags(tags: string[]): string[] {
  // 移除标签中的#前缀
  const cleanTags = tags.map(tag => tag.replace(/^#\s*/, ''));
  
  // 将标签按空格分割成单词
  const words = cleanTags.flatMap(tag => tag.split(/[\s-]+/));
  
  // 统计词频
  const wordCount = words.reduce((acc, word) => {
    acc[word] = (acc[word] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  // 按频率排序并返回前3个词（增加到3个以提供更多组合可能）
  return Object.entries(wordCount)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([word]) => word);
}

/**
 * 从服务器标题中提取关键词
 */
function extractKeywordsFromTitles(titles: string[]): string[] {
  // 将所有标题合并并分词
  const words = titles.flatMap(title => 
    title.split(/[\s-]+/).map(word => word.toLowerCase())
  );
  
  // 过滤掉常见的无意义词
  const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']);
  const filteredWords = words.filter(word => !stopWords.has(word));
  
  // 统计词频
  const wordCount = filteredWords.reduce((acc, word) => {
    acc[word] = (acc[word] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  // 按频率排序并返回前3个词（增加到3个以提供更多组合可能）
  return Object.entries(wordCount)
    .sort(([, a], [, b]) => b - a)
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
 * 为所有cluster生成名称
 */
export function generateClusterNames(clusters: ClusterSummary[]): ClusterSummary[] {
  const existingNames = new Set<string>();
  
  return clusters.map(cluster => {
    // 获取所有可能的关键词
    const tagKeywords = extractKeywordsFromTags(cluster.common_tags);
    const titleKeywords = extractKeywordsFromTitles(cluster.servers.map(s => s.title));
    const allKeywords = [...new Set([...tagKeywords, ...titleKeywords])];
    
    // 生成基础名称
    const baseName = generateBaseName(cluster);
    
    // 生成唯一名称
    const uniqueName = generateUniqueName(baseName, cluster, existingNames, allKeywords);
    
    // 将生成的名称添加到已存在集合中
    existingNames.add(uniqueName);
    
    return {
      ...cluster,
      cluster_name: uniqueName
    };
  });
} 