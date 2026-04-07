// 搜索语法 Token 解析与协议转换工具

export type TokenType = 'tag' | 'author' | 'channel' | 'text';
export type SearchTokenMode = 'include' | 'exclude';

export interface SearchToken {
  type: TokenType;
  value: string;
  raw: string; // 原始文本，包括 $tag:xxx$ / -$tag:xxx$ 格式
  start: number;
  end: number;
  mode: SearchTokenMode;
}

export interface TokenizedSearchPayload {
  text: string;
  includeTags: string[];
  excludeTags: string[];
  includeAuthors: string[];
  excludeAuthors: string[];
  channels: string[];
}

function dedupe(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

/**
 * 解析搜索查询字符串，识别：
 * - $tag:xxx$
 * - -$tag:xxx$
 * - $author:xxx$
 * - -$author:xxx$
 * - $channel:xxx$
 */
export function parseSearchQuery(query: string): SearchToken[] {
  const tokens: SearchToken[] = [];

  // 支持可选负号前缀，例如 -$tag:xxx$
  const tokenRegex = /(-)?\$(tag|author|channel):([^$]+)\$/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenRegex.exec(query)) !== null) {
    const [fullMatch, negativeFlag, type, value] = match;
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
          mode: 'include',
        });
      }
    }

    tokens.push({
      type: type as TokenType,
      value: value.trim(),
      raw: fullMatch,
      start,
      end,
      mode: negativeFlag ? 'exclude' : 'include',
    });

    lastIndex = end;
  }

  if (lastIndex < query.length) {
    const textValue = query.substring(lastIndex).trim();
    if (textValue) {
      tokens.push({
        type: 'text',
        value: textValue,
        raw: textValue,
        start: lastIndex,
        end: query.length,
        mode: 'include',
      });
    }
  }

  return tokens;
}

/**
 * 将 tokens 重新组合成查询字符串
 */
export function tokensToQuery(tokens: SearchToken[]): string {
  return tokens.map((token) => token.raw).join(' ');
}

/**
 * 添加一个 token 到查询字符串
 */
export function addToken(
  query: string,
  type: Exclude<TokenType, 'text'>,
  value: string,
  mode: SearchTokenMode = 'include',
): string {
  const tokens = parseSearchQuery(query);
  const trimmedValue = value.trim();

  const exists = tokens.some(
    (token) => token.type === type && token.value === trimmedValue && token.mode === mode,
  );

  if (exists) {
    return query;
  }

  const raw = `${mode === 'exclude' ? '-' : ''}$${type}:${trimmedValue}$`;
  const newToken: SearchToken = {
    type,
    value: trimmedValue,
    raw,
    start: 0,
    end: 0,
    mode,
  };

  const nonTextTokens = tokens.filter((token) => token.type !== 'text');
  const textTokens = tokens.filter((token) => token.type === 'text');
  return tokensToQuery([...nonTextTokens, newToken, ...textTokens]);
}

/**
 * 从查询字符串中移除一个 token
 */
export function removeToken(query: string, tokenToRemove: SearchToken): string {
  const tokens = parseSearchQuery(query);
  const filtered = tokens.filter(
    (token) =>
      !(
        token.type === tokenToRemove.type
        && token.value === tokenToRemove.value
        && token.mode === tokenToRemove.mode
      ),
  );
  return tokensToQuery(filtered);
}

/**
 * 把查询拆解为 API / URL 层可消费的结构。
 */
export function tokenizeSearchPayload(query: string): TokenizedSearchPayload {
  const tokens = parseSearchQuery(query || '');

  const includeTags = tokens
    .filter((token) => token.type === 'tag' && token.mode === 'include')
    .map((token) => token.value);
  const excludeTags = tokens
    .filter((token) => token.type === 'tag' && token.mode === 'exclude')
    .map((token) => token.value);
  const includeAuthors = tokens
    .filter((token) => token.type === 'author' && token.mode === 'include')
    .map((token) => token.value);
  const excludeAuthors = tokens
    .filter((token) => token.type === 'author' && token.mode === 'exclude')
    .map((token) => token.value);
  const channels = tokens
    .filter((token) => token.type === 'channel' && token.mode === 'include')
    .map((token) => token.value);
  const text = tokens
    .filter((token) => token.type === 'text')
    .map((token) => token.value)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();

  return {
    text,
    includeTags: dedupe(includeTags),
    excludeTags: dedupe(excludeTags),
    includeAuthors: dedupe(includeAuthors),
    excludeAuthors: dedupe(excludeAuthors),
    channels: dedupe(channels),
  };
}

/**
 * 将旧的 author:xxx / channel:xxx / tag:xxx 语法转换为新的 token 语法。
 */
export function migrateLegacySyntax(query: string): string {
  return query
    .replace(/(^|\s)-author:(\S+)/g, '$1-$author:$2$')
    .replace(/(^|\s)-tag:(\S+)/g, '$1-$tag:$2$')
    .replace(/(^|\s)author:(\S+)/g, '$1$author:$2$')
    .replace(/(^|\s)channel:(\S+)/g, '$1$channel:$2$')
    .replace(/(^|\s)tag:(\S+)/g, '$1$tag:$2$');
}
