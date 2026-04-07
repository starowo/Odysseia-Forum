// 搜索历史管理工具

const SEARCH_HISTORY_KEY = 'odysseia_search_history';
const MAX_HISTORY_ITEMS = 10;

export interface SearchHistoryItem {
  query: string;
  timestamp: number;
}

// 获取搜索历史
export function getSearchHistory(): SearchHistoryItem[] {
  try {
    const history = localStorage.getItem(SEARCH_HISTORY_KEY);
    return history ? JSON.parse(history) : [];
  } catch (error) {
    console.error('Failed to load search history:', error);
    return [];
  }
}

// 添加搜索记录
export function addSearchHistory(query: string): void {
  if (!query.trim()) return;

  try {
    const history = getSearchHistory();
    
    // 移除重复项
    const filtered = history.filter(item => item.query !== query);
    
    // 添加新记录到开头
    const newHistory = [
      { query, timestamp: Date.now() },
      ...filtered,
    ].slice(0, MAX_HISTORY_ITEMS); // 限制数量
    
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(newHistory));
  } catch (error) {
    console.error('Failed to save search history:', error);
  }
}

// 删除单条搜索记录
export function removeSearchHistory(query: string): void {
  try {
    const history = getSearchHistory();
    const filtered = history.filter(item => item.query !== query);
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error('Failed to remove search history:', error);
  }
}

// 清空搜索历史
export function clearSearchHistory(): void {
  try {
    localStorage.removeItem(SEARCH_HISTORY_KEY);
  } catch (error) {
    console.error('Failed to clear search history:', error);
  }
}
