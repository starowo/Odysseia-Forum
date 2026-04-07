import { describe, it, expect } from 'vitest';
import { parseSearchQuery, addToken, removeToken, migrateLegacySyntax } from './searchTokenizer';

describe('searchTokenizer', () => {
  describe('parseSearchQuery', () => {
    it('应该能解析普通文本', () => {
      const query = 'hello world';
      const tokens = parseSearchQuery(query);
      expect(tokens).toHaveLength(1);
      expect(tokens[0]).toMatchObject({ type: 'text', value: 'hello world' });
    });

    it('应该能解析基础标签语法 $tag:xxx$', () => {
      const query = '$tag:AI$ 机器人';
      const tokens = parseSearchQuery(query);
      expect(tokens).toHaveLength(2);
      expect(tokens[0]).toMatchObject({ type: 'tag', value: 'AI' });
      expect(tokens[1]).toMatchObject({ type: 'text', value: '机器人' });
    });

    it('应该能解析作者语法 $author:xxx$', () => {
      const query = '$author:秋青子$';
      const tokens = parseSearchQuery(query);
      expect(tokens).toHaveLength(1);
      expect(tokens[0]).toMatchObject({ type: 'author', value: '秋青子' });
    });

    it('应该能处理混合语法并自动修剪空格', () => {
      const query = '  $tag:游戏$   $author:哥哥$   关键字  ';
      const tokens = parseSearchQuery(query);
      expect(tokens).toHaveLength(3);
      expect(tokens[0].value).toBe('游戏');
      expect(tokens[1].value).toBe('哥哥');
      expect(tokens[2].value).toBe('关键字');
    });
  });

  describe('addToken', () => {
    it('应该能向空查询添加新 token', () => {
      const result = addToken('', 'tag', 'React');
      expect(result).toBe('$tag:React$');
    });

    it('不应该重复添加相同的 token', () => {
      const query = '$tag:React$';
      const result = addToken(query, 'tag', 'React');
      expect(result).toBe(query);
    });

    it('应该能在现有文本后追加 token', () => {
      const query = 'hello';
      const result = addToken(query, 'tag', 'world');
      expect(result).toBe('hello $tag:world$');
    });
  });

  describe('removeToken', () => {
    it('应该能移除指定的 token', () => {
      const query = 'hello $tag:world$';
      const tokens = parseSearchQuery(query);
      const tagToken = tokens.find(t => t.type === 'tag')!;
      const result = removeToken(query, tagToken);
      expect(result).toBe('hello');
    });
  });

  describe('migrateLegacySyntax', () => {
    it('应该将 legacy author:xxx 转换为新的 $author:xxx$ 格式', () => {
      const query = 'author:anthropic rocks';
      const result = migrateLegacySyntax(query);
      expect(result).toBe('$author:anthropic$ rocks');
    });
  });
});
