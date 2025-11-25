import { History, Hash, MessageCircle, X, Clock } from 'lucide-react';
import { getSearchHistory, removeSearchHistory, clearSearchHistory } from '@/lib/searchHistory';
import { useState, useEffect, useRef, useMemo } from 'react';

interface SearchSuggestionsProps {
    isOpen: boolean;
    currentQuery: string;
    availableTags?: string[];
    channels?: Array<{ id: string; name: string }>;
    onSelect: (suggestion: string) => void;
    onClose: () => void;
    inputRef?: React.RefObject<HTMLInputElement>;
}

export function SearchSuggestions({
    isOpen,
    currentQuery,
    availableTags = [],
    channels = [],
    onSelect,
    onClose,
    inputRef,
}: SearchSuggestionsProps) {
    const [history, setHistory] = useState(getSearchHistory());
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [selectedIndex, setSelectedIndex] = useState(-1);

    // 更新历史记录
    useEffect(() => {
        const handleStorageChange = () => {
            setHistory(getSearchHistory());
        };

        window.addEventListener('storage', handleStorageChange);
        return () => window.removeEventListener('storage', handleStorageChange);
    }, []);

    // 点击外部关闭
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node) &&
                inputRef?.current &&
                !inputRef.current.contains(event.target as Node)
            ) {
                onClose();
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen, onClose, inputRef]);

    // 生成建议列表
    const suggestions = useMemo(() => {
        const result: Array<{
            type: 'history' | 'tag' | 'channel';
            value: string;
            display: string;
        }> = [];

        // 历史记录（最多 5 条）
        const recentHistory = history.slice(0, 5);
        recentHistory.forEach((item) => {
            result.push({
                type: 'history',
                value: item.query,
                display: item.query,
            });
        });

        // 标签建议（过滤当前查询中已有的标签，最多 5 条）
        const queryLower = currentQuery.toLowerCase();
        const existingTags = currentQuery.match(/\$tag:([^$]+)\$/g) || [];
        const existingTagNames = existingTags
            .map((t) => t.match(/\$tag:([^$]+)\$/)?.[1])
            .filter(Boolean);

        const relevantTags = availableTags
            .filter((tag) => {
                // 过滤已存在的标签
                if (existingTagNames.includes(tag)) return false;
                // 如果有输入，优先显示包含输入的标签
                return !currentQuery.trim() || tag.toLowerCase().includes(queryLower);
            })
            .slice(0, 5);

        relevantTags.forEach((tag) => {
            result.push({
                type: 'tag',
                value: ` $tag:${tag}$`,
                display: tag,
            });
        });

        // 频道建议（最多 5 条）
        const relevantChannels = channels
            .filter((ch) => !currentQuery.trim() || ch.name.toLowerCase().includes(queryLower))
            .slice(0, 5);

        relevantChannels.forEach((ch) => {
            result.push({
                type: 'channel',
                value: ` $channel:${ch.id}$`,
                display: ch.name,
            });
        });

        return result;
    }, [history, currentQuery, availableTags, channels]);

    // 键盘导航
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!isOpen) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                handleSelect(suggestions[selectedIndex].value);
            } else if (e.key === 'Escape') {
                onClose();
            }
        };

        inputRef?.current?.addEventListener('keydown', handleKeyDown);
        return () => {
            inputRef?.current?.removeEventListener('keydown', handleKeyDown);
        };
    }, [isOpen, selectedIndex, suggestions, inputRef]);

    // 重置选中索引
    useEffect(() => {
        if (isOpen) {
            setSelectedIndex(-1);
        }
    }, [isOpen, currentQuery]);

    const handleRemove = (query: string, e: React.MouseEvent) => {
        e.stopPropagation();
        removeSearchHistory(query);
        setHistory(getSearchHistory());
    };

    const handleClearAll = (e: React.MouseEvent) => {
        e.stopPropagation();
        clearSearchHistory();
        setHistory([]);
    };

    const handleSelect = (value: string) => {
        onSelect(value);
        onClose();
    };

    if (!isOpen || suggestions.length === 0) {
        return null;
    }

    const getIcon = (type: string) => {
        switch (type) {
            case 'history':
                return <Clock className="h-4 w-4" />;
            case 'tag':
                return <Hash className="h-4 w-4" />;
            case 'channel':
                return <MessageCircle className="h-4 w-4" />;
            default:
                return null;
        }
    };

    const getLabel = (type: string) => {
        switch (type) {
            case 'history':
                return '历史搜索';
            case 'tag':
                return '标签建议';
            case 'channel':
                return '频道';
            default:
                return '';
        }
    };

    // 按类型分组
    const grouped = suggestions.reduce((acc, suggestion) => {
        if (!acc[suggestion.type]) {
            acc[suggestion.type] = [];
        }
        acc[suggestion.type].push(suggestion);
        return acc;
    }, {} as Record<string, typeof suggestions>);

    return (
        <div
            ref={dropdownRef}
            className="absolute left-0 right-0 top-full z-50 mt-2 rounded-lg border border-[var(--od-border-strong)] bg-[var(--od-bg-secondary)] shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200"
        >
            {/* 标题栏 */}
            <div className="flex items-center justify-between border-b border-[var(--od-border-strong)] px-4 py-3">
                <div className="flex items-center gap-2">
                    <History className="h-4 w-4 text-[var(--od-text-tertiary)]" />
                    <span className="text-sm font-semibold text-[var(--od-text-primary)]">搜索建议</span>
                </div>
                {history.length > 0 && (
                    <button
                        onClick={handleClearAll}
                        className="text-xs text-[var(--od-text-tertiary)] transition-colors hover:text-[var(--od-text-primary)]"
                    >
                        清空历史
                    </button>
                )}
            </div>

            {/* 建议列表 */}
            <div className="max-h-[400px] overflow-y-auto">
                {Object.entries(grouped).map(([type, items], groupIndex) => (
                    <div key={type} className={groupIndex > 0 ? 'border-t border-[var(--od-border)]' : ''}>
                        {/* 分组标题 */}
                        <div className="px-4 py-2 text-xs font-medium text-[var(--od-text-tertiary)]">
                            {getLabel(type)}
                        </div>

                        {/* 分组项 */}
                        {items.map((suggestion, itemIndex) => {
                            const globalIndex = suggestions.indexOf(suggestion);
                            const isSelected = globalIndex === selectedIndex;

                            return (
                                <button
                                    key={`${type}-${itemIndex}`}
                                    onClick={() => handleSelect(suggestion.value)}
                                    className={`group flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${isSelected
                                        ? 'bg-[var(--od-accent)]/20 text-[var(--od-text-primary)]'
                                        : 'hover:bg-[var(--od-bg-tertiary)]'
                                        }`}
                                >
                                    <span
                                        className={`flex-shrink-0 ${isSelected ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-tertiary)]'
                                            }`}
                                    >
                                        {getIcon(type)}
                                    </span>
                                    <span className="flex-1 truncate text-sm text-[var(--od-text-primary)]">
                                        {suggestion.display}
                                    </span>
                                    {type === 'history' && (
                                        <button
                                            onClick={(e) => handleRemove(suggestion.value, e)}
                                            className="flex-shrink-0 rounded p-1 opacity-0 transition-all hover:bg-[var(--od-card-hover)] group-hover:opacity-100"
                                            title="删除"
                                        >
                                            <X className="h-3.5 w-3.5 text-[var(--od-text-tertiary)]" />
                                        </button>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                ))}
            </div>

            {/* 提示信息 */}
            <div className="border-t border-[var(--od-border)] px-4 py-2 text-xs text-[var(--od-text-tertiary)]">
                <span>使用</span>
                <kbd className="mx-1 rounded bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 font-mono">↑</kbd>
                <kbd className="mx-1 rounded bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 font-mono">↓</kbd>
                <span>选择，</span>
                <kbd className="mx-1 rounded bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 font-mono">Enter</kbd>
                <span>确认</span>
            </div>
        </div>
    );
}
