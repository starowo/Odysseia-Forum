import { History, Hash, MessageCircle, X, Clock, Flame, User } from 'lucide-react';
import { getSearchHistory, removeSearchHistory, clearSearchHistory } from '@/shared/lib/searchHistory';
import { useState, useEffect, useRef, useMemo } from 'react';
import { motion } from 'framer-motion';

interface SearchSuggestionsProps {
    currentQuery: string;
    availableTags?: string[];
    channels?: Array<{ id: string; name: string }>;
    authors?: Array<{ name: string; avatar?: string }>; // 未来接入后端作者清单用
    onSelect: (suggestion: string) => void;
    onClose: () => void;
    inputRef?: React.RefObject<HTMLInputElement>;
}

export function SearchSuggestions({
    currentQuery,
    availableTags = [],
    channels = [],
    authors = [],
    onSelect,
    onClose,
    inputRef,
}: SearchSuggestionsProps) {
    const [history, setHistory] = useState(getSearchHistory());
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [selectedIndex, setSelectedIndex] = useState(-1);

    // 随机数生成器 (简单实现，仅用于由于没有推荐算法而用来“猜你想搜”)
    const randomTags = useMemo(() => {
        if (availableTags.length === 0) return [];
        const shuffled = [...availableTags].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, 5);
    }, [availableTags]);

    // 更新历史记录
    useEffect(() => {
        const handleStorageChange = () => setHistory(getSearchHistory());
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
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose, inputRef]);

    const isZeroState = !currentQuery.trim();

    // 生成建议列表结构
    const groups = useMemo(() => {
        const queryLower = currentQuery.toLowerCase();
        
        let flatItems: any[] = [];
        let sectionedGroups: { title: string, icon: any, items: any[] }[] = [];

        if (isZeroState) {
            // Zero-State: 历史搜索 和 猜你想搜
            const historyItems = history.slice(0, 5).map(h => ({
                type: 'history', value: h.query, display: h.query, icon: Clock 
            }));
            if (historyItems.length > 0) {
                sectionedGroups.push({ title: '历史搜索', icon: History, items: historyItems });
                flatItems.push(...historyItems);
            }

            const popTags = randomTags.map(t => ({
                type: 'tag', value: ` $tag:${t}$`, display: t, icon: Flame
            }));
            if (popTags.length > 0) {
                sectionedGroups.push({ title: '猜你想搜', icon: Flame, items: popTags });
                flatItems.push(...popTags);
            }
        } else {
            // 有输入时: 匹配标签、频道、作者
            const existingTags = currentQuery.match(/\$tag:([^$]+)\$/g) || [];
            const existingTagNames = existingTags.map((t) => t.match(/\$tag:([^$]+)\$/)?.[1]).filter(Boolean);

            const relevantTags = availableTags
                .filter(tag => !existingTagNames.includes(tag) && tag.toLowerCase().includes(queryLower))
                .slice(0, 5)
                .map(tag => ({ type: 'tag', value: ` $tag:${tag}$`, display: tag, icon: Hash }));

            if (relevantTags.length > 0) {
                sectionedGroups.push({ title: '相关标签', icon: Hash, items: relevantTags });
                flatItems.push(...relevantTags);
            }

            const relevantChannels = channels
                .filter((ch) => ch.name.toLowerCase().includes(queryLower))
                .slice(0, 5)
                .map(ch => ({ type: 'channel', value: ` $channel:${ch.id}$`, display: ch.name, icon: MessageCircle }));

            if (relevantChannels.length > 0) {
                sectionedGroups.push({ title: '频道直达', icon: MessageCircle, items: relevantChannels });
                flatItems.push(...relevantChannels);
            }

            const relevantAuthors = authors
                .filter(a => a.name.toLowerCase().includes(queryLower))
                .slice(0, 5)
                .map(a => ({ type: 'author', value: ` $author:${a.name}$`, display: a.name, icon: User, avatar: a.avatar }));

            if (relevantAuthors.length > 0) {
                sectionedGroups.push({ title: '匹配作者', icon: User, items: relevantAuthors });
                flatItems.push(...relevantAuthors);
            }
        }
        
        return { sectionedGroups, flatItems };
    }, [history, currentQuery, availableTags, channels, authors, isZeroState, randomTags]);

    // 键盘导航
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex((prev) => (prev < groups.flatItems.length - 1 ? prev + 1 : prev));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                handleSelect(groups.flatItems[selectedIndex].value);
            } else if (e.key === 'Escape') {
                onClose();
            }
        };

        inputRef?.current?.addEventListener('keydown', handleKeyDown);
        return () => inputRef?.current?.removeEventListener('keydown', handleKeyDown);
    }, [selectedIndex, groups.flatItems, inputRef, onClose]);

    // 重置选中索引
    useEffect(() => {
        setSelectedIndex(-1);
    }, [currentQuery]);

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
    };

    if (groups.flatItems.length === 0) {
        return null;
    }

    return (
        <motion.div
            ref={dropdownRef}
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="absolute right-0 top-full z-50 mt-od-sm w-full sm:w-[500px] overflow-hidden rounded-lg border border-[var(--od-border-strong)] bg-[var(--od-bg-secondary)] shadow-2xl origin-top"
        >
            <div className={`flex max-h-[400px] flex-col sm:flex-row divide-y sm:divide-y-0 sm:divide-x divide-[var(--od-border)]`}>
                {groups.sectionedGroups.map((group) => (
                    <div key={group.title} className="flex-1 p-od-sm">
                        <div className="flex items-center justify-between mb-od-sm px-1">
                            <div className="flex items-center gap-1.5 text-od-xs font-od-bold text-[var(--od-text-tertiary)]">
                                <group.icon className="w-3.5 h-3.5" />
                                {group.title}
                            </div>
                            {group.title === '历史搜索' && history.length > 0 && (
                                <button
                                    onClick={handleClearAll}
                                    className="text-od-xs text-[var(--od-text-tertiary)] hover:text-[var(--od-error)] transition-colors"
                                >
                                    清空
                                </button>
                            )}
                        </div>
                        <ul className="space-y-1">
                            {group.items.map((item) => {
                                const globalIndex = groups.flatItems.indexOf(item);
                                const isSelected = selectedIndex === globalIndex;
                                return (
                                    <li key={globalIndex}>
                                        <div
                                            role="button"
                                            tabIndex={0}
                                            onClick={() => handleSelect(item.value)}
                                            onKeyDown={(e) => { if(e.key === 'Enter') handleSelect(item.value); }}
                                            className={`group flex w-full items-center justify-between gap-od-sm rounded-md px-2.5 py-1.5 text-left transition-colors cursor-pointer ${
                                                isSelected ? 'bg-[var(--od-accent)]/20 text-[var(--od-text-primary)]' : 'hover:bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)]'
                                            }`}
                                        >
                                            <div className="flex items-center gap-od-sm overflow-hidden">
                                                {item.type === 'author' && item.avatar ? (
                                                    <img src={item.avatar} alt="avatar" className="w-5 h-5 rounded-full object-cover" />
                                                ) : (
                                                    <item.icon className={`flex-shrink-0 w-4 h-4 ${isSelected ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-tertiary)]'}`} />
                                                )}
                                                <span className="truncate text-od-sm font-od-medium">{item.display}</span>
                                            </div>
                                            {item.type === 'history' && (
                                                <button
                                                    onClick={(e) => handleRemove(item.value, e)}
                                                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-[var(--od-card-hover)] rounded"
                                                >
                                                    <X className="w-3.5 h-3.5 text-[var(--od-text-tertiary)]" />
                                                </button>
                                            )}
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                ))}
            </div>
            {/* 底部键盘指引 */}
            <div className="border-t border-[var(--od-border)] bg-[var(--od-bg-tertiary)]/50 p-od-sm text-od-xs text-[var(--od-text-tertiary)] flex items-center justify-between">
                <div>
                   智能搜索导航
                </div>
                <div className="flex items-center gap-od-sm">
                    <span className="flex items-center gap-1">
                        <kbd className="rounded bg-[var(--od-border)] px-1 font-mono">↑</kbd>
                        <kbd className="rounded bg-[var(--od-border)] px-1 font-mono">↓</kbd> 切换
                    </span>
                    <span className="flex items-center gap-1">
                        <kbd className="rounded bg-[var(--od-border)] px-1 font-mono">↵</kbd> 确认
                    </span>
                </div>
            </div>
        </motion.div>
    );
}
