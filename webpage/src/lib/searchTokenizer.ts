// 搜索语法 Token 解析工具

export type TokenType = 'tag' | 'author' | 'text';

export interface SearchToken {
  type: TokenType;
  value: string;
  raw: string; // 原始文本，包括 $tag:xxx$ 格式
  start: number;
  end: number;
}

/**
 * 解析搜索查询字符串，识别 $tag:xxx$ 和 $author:xxx$ 语法
 * @param query 搜索查询字符串
 * @returns Token 数组
 */
export function parseSearchQuery(query: string): SearchToken[] {
  const tokens: SearchToken[] = [];
  
  // 匹配 $tag:xxx$ 或 $author:xxx$ 格式
  const tokenRegex = /\$(tag|author):([^$]+)\$/g;
  let lastIndex = 0;
  let match;

  while ((match = tokenRegex.exec(query)) !== null) {
    const [fullMatch, type, value] = match;
    const start = match.index;
    const end = start + fullMatch.length;

    // 添加之前的普通文本
    if (start > lastIndex) {
      const textValue = query.substring(lastIndex, start).trim();
      if (textValue) {
        tokens.push({
          type: 'text',
          value: textValue,
          raw: textValue,
          start: lastIndex,
          end: start,
        });
      }
    }

    // 添加 token
    tokens.push({
      type: type as TokenType,
      value: value.trim(),
      raw: fullMatch,
      start,
      end,
    });

    lastIndex = end;
  }

  // 添加剩余的普通文本
  if (lastIndex < query.length) {
    const textValue = query.substring(lastIndex).trim();
    if (textValue) {
      tokens.push({
        type: 'text',
        value: textValue,
        raw: textValue,
        start: lastIndex,
        end: query.length,
      });
    }
  }

  return tokens;
}

/**
 * 将 tokens 重新组合成查询字符串
 * @param tokens Token 数组
 * @returns 查询字符串
 */
export function tokensToQuery(tokens: SearchToken[]): string {
  return tokens.map(token => token.raw).join(' ');
}

/**
 * 添加一个 token 到查询字符串
 * @param query 当前查询字符串
 * @param type Token 类型
 * @param value Token 值
 * @returns 新的查询字符串
 */
export function addToken(query: string, type: TokenType, value: string): string {
  const tokens = parseSearchQuery(query);
  
  // 检查是否已存在相同的 token
  const exists = tokens.some(
    token => token.type === type && token.value === value
  );
  
  if (exists) {
    return query;
  }

  // 添加新 token
  const newToken: SearchToken = {
    type,
    value,
    raw: `$${type}:${value}$`,
    start: 0,
    end: 0,
  };

  tokens.push(newToken);
  return tokensToQuery(tokens);
}

/**
 * 从查询字符串中移除一个 token
 * @param query 当前查询字符串
 * @param tokenToRemove 要移除的 token
 * @returns 新的查询字符串
 */
export function removeToken(query: string, tokenToRemove: SearchToken): string {
  const tokens = parseSearchQuery(query);
  const filtered = tokens.filter(
    token => !(token.type === tokenToRemove.type && token.value === tokenToRemove.value)
  );
  return tokensToQuery(filtered);
}

/**
 * 将旧的 author:xxx 语法转换为新的 $author:xxx$ 语法
 * @param query 查询字符串
 * @returns 转换后的查询字符串
 */
export function migrateLegacySyntax(query: string): string {
  // 匹配 author:xxx (后面跟空格或结束)
  return query.replace(/author:(\S+)/g, '$author:$1$');
}