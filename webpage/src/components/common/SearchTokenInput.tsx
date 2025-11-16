import { useRef, useState, useEffect, KeyboardEvent } from 'react';
import { X, Tag as TagIcon, User } from 'lucide-react';
import { parseSearchQuery, removeToken, SearchToken, tokensToQuery } from '@/lib/searchTokenizer';

interface SearchTokenInputProps {
  value: string;
  onChange: (value: string) => void;
  onSearch?: () => void;
  placeholder?: string;
  className?: string;
}

export function SearchTokenInput({
  value,
  onChange,
  onSearch,
  placeholder = '搜索...',
  className = '',
}: SearchTokenInputProps) {
  const [tokens, setTokens] = useState<SearchToken[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 解析 value 到 tokens
  useEffect(() => {
    const parsed = parseSearchQuery(value);
    setTokens(parsed);
    
    // 如果只有文本 token，显示在输入框中
    if (parsed.length === 1 && parsed[0].type === 'text') {
      setInputValue(parsed[0].value);
    } else if (parsed.length === 0) {
      setInputValue('');
    } else {
      // 提取非文本 token 后的文本部分
      const lastToken = parsed[parsed.length - 1];
      if (lastToken.type === 'text') {
        setInputValue(lastToken.value);
      } else {
        setInputValue('');
      }
    }
  }, [value]);

  const handleRemoveToken = (token: SearchToken) => {
    const newQuery = removeToken(value, token);
    onChange(newQuery);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    
    // 更新完整查询
    const nonTextTokens = tokens.filter(t => t.type !== 'text');
    const newQuery = nonTextTokens.length > 0
      ? `${tokensToQuery(nonTextTokens)} ${newValue}`.trim()
      : newValue;
    
    onChange(newQuery);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Enter 键触发搜索
    if (e.key === 'Enter') {
      e.preventDefault();
      onSearch?.();
      inputRef.current?.blur();
      return;
    }

    // Backspace 删除最后一个 token
    if (e.key === 'Backspace' && inputValue === '' && tokens.length > 0) {
      const lastNonTextToken = [...tokens].reverse().find(t => t.type !== 'text');
      if (lastNonTextToken) {
        handleRemoveToken(lastNonTextToken);
      }
    }
  };

  const getTokenIcon = (type: SearchToken['type']) => {
    switch (type) {
      case 'tag':
        return <TagIcon className="h-3 w-3" />;
      case 'author':
        return <User className="h-3 w-3" />;
      default:
        return null;
    }
  };

  const getTokenColor = (type: SearchToken['type']) => {
    switch (type) {
      case 'tag':
        return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'author':
        return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
      default:
        return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20';
    }
  };

  return (
    <div
      ref={containerRef}
      onClick={() => inputRef.current?.focus()}
      className={`flex min-h-[40px] w-full flex-wrap items-center gap-2 rounded-lg border-none bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus-within:bg-[var(--od-bg-tertiary)] focus-within:ring-2 focus-within:ring-[var(--od-accent)]/60 ${className}`}
    >
      {/* 显示 token chips */}
      {tokens
        .filter(token => token.type !== 'text')
        .map((token, index) => (
          <div
            key={`${token.type}-${token.value}-${index}`}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-all duration-200 hover:scale-105 ${getTokenColor(token.type)}`}
          >
            {getTokenIcon(token.type)}
            <span className="max-w-[120px] truncate">{token.value}</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleRemoveToken(token);
              }}
              className="rounded-full p-0.5 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
              aria-label={`移除 ${token.type}: ${token.value}`}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}

      {/* 输入框 */}
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsEditing(true)}
        onBlur={() => setIsEditing(false)}
        placeholder={tokens.length === 0 ? placeholder : ''}
        className="min-w-[120px] flex-1 bg-transparent text-[var(--od-text-primary)] placeholder:text-[var(--od-text-tertiary)] focus:outline-none"
      />
    </div>
  );
}