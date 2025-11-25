import { useRef, useState, useEffect, KeyboardEvent } from 'react';
import { X, Tag as TagIcon, User } from 'lucide-react';
import { parseSearchQuery, removeToken, SearchToken, tokensToQuery } from '@/lib/searchTokenizer';

interface SearchTokenInputProps {
  value: string;
  onChange: (value: string) => void;
  onSearch?: () => void;
  onFocus?: () => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
}

export function SearchTokenInput({
  value,
  onChange,
  onSearch,
  onFocus,
  onBlur,
  placeholder = '搜索...',
  className = '',
}: SearchTokenInputProps) {
  const [tokens, setTokens] = useState<SearchToken[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [editingTokenIndex, setEditingTokenIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const editInputRefs = useRef<Map<number, HTMLInputElement>>(new Map());

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

  // 监听 tokens 变化，如果有空的 token (来自模板)，自动聚焦到输入框
  useEffect(() => {
    const emptyTokenIndex = tokens.findIndex(t => t.type !== 'text' && !t.value);
    if (emptyTokenIndex !== -1) {
      // 如果有空 token，我们实际上不需要做特殊处理，因为渲染逻辑会把它变成 input
      // 但我们需要确保 inputRef 聚焦
      // 这里稍微复杂点：如果我们在渲染列表里放 input，那 inputRef 指向的是主输入框
      // 我们需要为每个 token chip 准备 ref 吗？
      // 简化方案：点击模板 -> 插入 "$type:$" -> 解析出空 token -> 渲染为带 input 的 chip -> 自动聚焦
    }
  }, [tokens]);

  const handleRemoveToken = (token: SearchToken) => {
    const newQuery = removeToken(value, token);
    onChange(newQuery);
  };

  // 点击 Token：进入编辑模式，在 token 位置显示输入框
  const handleTokenClick = (token: SearchToken) => {
    const nonTextTokens = tokens.filter(t => t.type !== 'text');
    const tokenIndex = nonTextTokens.indexOf(token);

    setEditingTokenIndex(tokenIndex);
    setEditingValue(token.value);

    // 聚焦到编辑输入框
    setTimeout(() => {
      const editInput = editInputRefs.current.get(tokenIndex);
      editInput?.focus();
      editInput?.select();
    }, 0);
  };

  // 完成 token 编辑
  const handleFinishEdit = (token: SearchToken, newValue: string) => {
    if (!newValue.trim()) {
      // 如果值为空，删除 token
      handleRemoveToken(token);
    } else {
      // 更新 token 值
      const newQuery = value.replace(token.raw, `$${token.type}:${newValue}$`);
      onChange(newQuery);
    }
    setEditingTokenIndex(null);
    setEditingValue('');
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingTokenIndex(null);
    setEditingValue('');
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
        .map((token, index) => {
          const isEditing = editingTokenIndex === index;

          return (
            <div
              key={`${token.type}-${token.value}-${index}`}
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-all duration-200 ${isEditing ? 'ring-2 ring-[var(--od-accent)]' : 'hover:scale-105'
                } ${getTokenColor(token.type)}`}
            >
              {getTokenIcon(token.type)}

              {isEditing ? (
                <input
                  ref={(el) => {
                    if (el) editInputRefs.current.set(index, el);
                  }}
                  type="text"
                  value={editingValue}
                  onChange={(e) => setEditingValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleFinishEdit(token, editingValue);
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      handleCancelEdit();
                    }
                  }}
                  onBlur={() => handleFinishEdit(token, editingValue)}
                  className="min-w-[60px] max-w-[120px] bg-transparent outline-none"
                  style={{ width: `${Math.max(60, editingValue.length * 8)}px` }}
                />
              ) : (
                <span
                  className="max-w-[120px] truncate cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTokenClick(token);
                  }}
                  title="点击修改"
                >
                  {token.value || '(空)'}
                </span>
              )}

              {!isEditing && (
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
              )}
            </div>
          );
        })}

      {/* 输入框 */}
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={onFocus}
        onBlur={onBlur}
        placeholder={tokens.length === 0 ? placeholder : ''}
        className="min-w-[120px] flex-1 bg-transparent text-[var(--od-text-primary)] placeholder:text-[var(--od-text-tertiary)] focus:outline-none"
      />
    </div>
  );
}