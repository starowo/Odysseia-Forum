import { describe, it, expect } from 'vitest';
import { parseParams, serializeParams } from './useSearchParams';

describe('useSearchParams URL 协议层', () => {
  describe('parseParams', () => {
    it('对于空 URL 参数应该返回默认值', () => {
      const sp = new URLSearchParams('');
      const params = parseParams(sp);
      expect(params.query).toBe('');
      expect(params.sortMethod).toBe('last_active_desc');
      expect(params.includeTags).toEqual([]);
    });

    it('应该能解析查询词和频道', () => {
      const sp = new URLSearchParams('q=hello&channel=tech');
      const params = parseParams(sp);
      expect(params.query).toBe('hello');
      expect(params.channel).toBe('tech');
    });

    it('应该能解析逗号分隔的标签', () => {
      const sp = new URLSearchParams('tags=AI,LLM&exclude=Spam');
      const params = parseParams(sp);
      expect(params.includeTags).toEqual(['AI', 'LLM']);
      expect(params.excludeTags).toEqual(['Spam']);
    });

    it('应该能处理非法的排序方式并回退到默认值', () => {
      const sp = new URLSearchParams('sort=invalid_sort');
      const params = parseParams(sp);
      expect(params.sortMethod).toBe('last_active_desc');
    });

    it('应该能正确解析排序方式', () => {
      const sp = new URLSearchParams('sort=created_desc');
      const params = parseParams(sp);
      expect(params.sortMethod).toBe('created_desc');
    });
  });

  describe('serializeParams', () => {
    it('空属性不应该被序列化到 URL', () => {
      const sp = serializeParams({ query: '' });
      expect(sp.toString()).toBe('');
    });

    it('默认值不应该被序列化到 URL 以保持简洁', () => {
      const sp = serializeParams({ sortMethod: 'last_active_desc', tagLogic: 'and' });
      expect(sp.toString()).toBe('');
    });

    it('应该能正确序列化标签数组', () => {
      const sp = serializeParams({ includeTags: ['A', 'B'] });
      expect(sp.get('tags')).toBe('A,B');
    });

    it('合并参数后的完整序列化', () => {
      const sp = serializeParams({
        query: 'search',
        channel: 'news',
        sortMethod: 'relevance',
        tagLogic: 'or'
      });
      expect(sp.get('q')).toBe('search');
      expect(sp.get('channel')).toBe('news');
      expect(sp.get('sort')).toBe('relevance');
      expect(sp.get('tag_logic')).toBe('or');
    });
  });
});
