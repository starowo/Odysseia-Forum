import type {
  SearchSuggestionAuthor,
  SearchSuggestionThread,
} from '@/features/search/api/searchApi';
import { Clock, FileText, Flame, Hash, History, MessageCircle, User, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { describeSearchHistoryContext, type SearchHistoryItem } from '@/shared/lib/searchHistory';

export type SearchSuggestionAction =
  | { type: 'append'; value: string }
  | { type: 'replace_query'; value: string; submit?: boolean }
  | { type: 'apply_history'; item: SearchHistoryItem }
  | { type: 'open_thread'; threadId: string; thread?: SearchSuggestionThread['source_thread'] };

interface SearchSuggestionsProps {
  currentQuery: string;
  availableTags?: string[];
  channels?: Array<{ id: string; name: string }>;
  authors?: SearchSuggestionAuthor[];
  threads?: SearchSuggestionThread[];
  history?: SearchHistoryItem[];
  suggestedTags?: string[];
  onSelect: (action: SearchSuggestionAction) => void;
  onClose: () => void;
  onRemoveHistory?: (item: SearchHistoryItem) => void;
  onClearHistory?: () => void;
  inputRef?: React.RefObject<HTMLInputElement>;
  embedded?: boolean;
  preferenceAware?: boolean;
}

export function SearchSuggestions({
  currentQuery,
  availableTags = [],
  channels = [],
  authors = [],
  threads = [],
  history = [],
  suggestedTags = [],
  onSelect,
  onClose,
  onRemoveHistory,
  onClearHistory,
  inputRef,
  embedded = false,
  preferenceAware = false,
}: SearchSuggestionsProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const randomTags = useMemo(() => {
    if (availableTags.length === 0) return [];
    const shuffled = [...availableTags].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, 5);
  }, [availableTags]);

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
  }, [inputRef, onClose]);

  type SuggestionItem =
    | {
        key: string;
        type: 'history';
        display: string;
        query: string;
        icon: typeof Clock;
        historyItem: SearchHistoryItem;
      }
    | {
        key: string;
        type: 'tag' | 'channel' | 'author';
        display: string;
        value: string;
        icon: typeof Hash | typeof MessageCircle | typeof User | typeof Flame;
        avatar?: string | null;
      }
    | {
        key: string;
        type: 'thread';
        display: string;
        threadId: string;
        icon: typeof FileText;
        snippet?: string | null;
        thumbnailUrl?: string | null;
        authorName?: string | null;
        authorAvatarUrl?: string | null;
        sourceThread?: SearchSuggestionThread['source_thread'];
      };

  const isZeroState = !currentQuery.trim();

  const groups = useMemo(() => {
    const queryLower = currentQuery.toLowerCase();
    const existingTags = currentQuery.match(/\$tag:([^$]+)\$/g) || [];
    const existingTagNames = existingTags
      .map((token) => token.match(/\$tag:([^$]+)\$/)?.[1] || '')
      .filter(Boolean);

    const flatItems: SuggestionItem[] = [];
    const sectionedGroups: Array<{ title: string; icon: any; items: SuggestionItem[] }> = [];

    if (isZeroState) {
      const historyItems: SuggestionItem[] = history.slice(0, 5).map((item, index) => ({
        key: `history-${item.id || item.timestamp}-${index}`,
        type: 'history',
        display: item.query,
        query: item.query,
        icon: Clock,
        historyItem: item,
      }));

      if (historyItems.length > 0) {
        sectionedGroups.push({ title: '历史搜索', icon: History, items: historyItems });
        flatItems.push(...historyItems);
      }

      const tagSource = suggestedTags.length > 0 ? suggestedTags : randomTags;
      const popularTags: SuggestionItem[] = tagSource.slice(0, 5).map((tag, index) => ({
        key: `tag-pop-${tag}-${index}`,
        type: 'tag',
        display: tag,
        value: ` $tag:${tag}$`,
        icon: Flame,
      }));

      if (popularTags.length > 0) {
        sectionedGroups.push({ title: '猜你想搜', icon: Flame, items: popularTags });
        flatItems.push(...popularTags);
      }
    } else {
      const relevantAuthors: SuggestionItem[] = authors
        .filter((author) => author.name.toLowerCase().includes(queryLower))
        .slice(0, 5)
        .map((author, index) => ({
          key: `author-${author.id}-${index}`,
          type: 'author',
          display: author.name,
          value: ` $author:${author.name}$`,
          avatar: author.avatar_url,
          icon: User,
        }));
      if (relevantAuthors.length > 0) {
        sectionedGroups.push({ title: '匹配作者', icon: User, items: relevantAuthors });
        flatItems.push(...relevantAuthors);
      }

      const directThreads: SuggestionItem[] = threads.slice(0, 5).map((thread, index) => ({
        key: `thread-${thread.thread_id}-${index}`,
        type: 'thread',
        display: thread.title,
        threadId: thread.thread_id,
        snippet: thread.snippet,
        thumbnailUrl: thread.thumbnail_url,
        authorName: thread.author_name,
        authorAvatarUrl: thread.author_avatar_url,
        sourceThread: thread.source_thread,
        icon: FileText,
      }));
      if (directThreads.length > 0) {
        sectionedGroups.push({ title: '帖子直达', icon: FileText, items: directThreads });
        flatItems.push(...directThreads);
      }

      const relevantTags: SuggestionItem[] = availableTags
        .filter((tag) => !existingTagNames.includes(tag) && tag.toLowerCase().includes(queryLower))
        .slice(0, 5)
        .map((tag, index) => ({
          key: `tag-${tag}-${index}`,
          type: 'tag',
          display: tag,
          value: ` $tag:${tag}$`,
          icon: Hash,
        }));
      if (relevantTags.length > 0) {
        sectionedGroups.push({ title: '相关标签', icon: Hash, items: relevantTags });
        flatItems.push(...relevantTags);
      }

      const relevantChannels: SuggestionItem[] = channels
        .filter((channel) => channel.name.toLowerCase().includes(queryLower))
        .slice(0, 5)
        .map((channel, index) => ({
          key: `channel-${channel.id}-${index}`,
          type: 'channel',
          display: channel.name,
          value: ` $channel:${channel.id}$`,
          icon: MessageCircle,
        }));
      if (relevantChannels.length > 0) {
        sectionedGroups.push({ title: '频道直达', icon: MessageCircle, items: relevantChannels });
        flatItems.push(...relevantChannels);
      }
    }

    return { sectionedGroups, flatItems };
  }, [authors, availableTags, channels, currentQuery, history, isZeroState, randomTags, suggestedTags, threads]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSelectedIndex((prev) => (prev < groups.flatItems.length - 1 ? prev + 1 : prev));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
      } else if (event.key === 'Enter' && selectedIndex >= 0) {
        event.preventDefault();
        handleSelect(groups.flatItems[selectedIndex]);
      } else if (event.key === 'Escape') {
        onClose();
      }
    };

    inputRef?.current?.addEventListener('keydown', handleKeyDown);
    return () => inputRef?.current?.removeEventListener('keydown', handleKeyDown);
  }, [groups.flatItems, inputRef, onClose, selectedIndex]);

  useEffect(() => {
    setSelectedIndex(-1);
  }, [currentQuery]);

  const handleSelect = (item: SuggestionItem) => {
    if (item.type === 'thread') {
      onSelect({ type: 'open_thread', threadId: item.threadId, thread: item.sourceThread });
      return;
    }

    if (item.type === 'history') {
      onSelect({ type: 'apply_history', item: item.historyItem });
      return;
    }

    onSelect({ type: 'append', value: item.value });
  };

  const content = (
    <>
      {groups.flatItems.length === 0 ? (
        <div className="p-4 text-sm text-[var(--od-text-tertiary)]">
          暂无联想结果，继续输入更多关键词试试。
        </div>
      ) : (
      <div className="max-h-[420px] overflow-y-auto p-2">
        {groups.sectionedGroups.map((group, groupIndex) => (
          <div
            key={group.title}
            className={`${groupIndex > 0 ? 'mt-2 border-t border-[var(--od-border)] pt-2' : ''}`}
          >
            <div className="mb-2 flex items-center justify-between px-1">
              <div className="flex items-center gap-1.5 text-od-xs font-od-bold text-[var(--od-text-tertiary)]">
                <group.icon className="h-3.5 w-3.5" />
                {group.title}
              </div>
              {group.title === '历史搜索' && history.length > 0 && (
                <button
                  onClick={() => onClearHistory?.()}
                  className="text-od-xs text-[var(--od-text-tertiary)] transition-colors hover:text-[var(--od-error)]"
                >
                  清空
                </button>
              )}
            </div>
            <ul className="space-y-1">
              {group.items.map((item) => {
                const globalIndex = groups.flatItems.findIndex((candidate) => candidate.key === item.key);
                const isSelected = selectedIndex === globalIndex;

                return (
                  <li key={item.key}>
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => handleSelect(item)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          handleSelect(item);
                        }
                      }}
                      className={`group flex w-full cursor-pointer items-center justify-between gap-2 rounded-md px-2.5 py-2 text-left transition-colors ${
                        isSelected
                          ? 'bg-[var(--od-accent)]/20 text-[var(--od-text-primary)]'
                          : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)]'
                      }`}
                    >
                      {item.type === 'thread' ? (
                        <div className="flex min-w-0 items-start gap-2">
                          <div className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-md bg-[var(--od-bg-tertiary)]">
                            {item.thumbnailUrl ? (
                              <img
                                src={item.thumbnailUrl}
                                alt={item.display}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <div className="flex h-full w-full items-center justify-center text-[var(--od-text-tertiary)]">
                                <FileText className="h-4 w-4" />
                              </div>
                            )}
                          </div>
                          <div className="min-w-0">
                            <div className="truncate text-sm font-semibold text-[var(--od-text-primary)]">
                              {item.display}
                            </div>
                            {item.snippet && (
                              <p className="line-clamp-2 text-xs text-[var(--od-text-tertiary)]">
                                {item.snippet}
                              </p>
                            )}
                            {item.authorName && (
                              <p className="mt-0.5 text-[11px] text-[var(--od-text-tertiary)]">
                                @{item.authorName}
                              </p>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="flex min-w-0 items-center gap-2 overflow-hidden">
                          {item.type === 'author' && item.avatar ? (
                            <img
                              src={item.avatar}
                              alt={item.display}
                              className="h-5 w-5 flex-shrink-0 rounded-full object-cover"
                            />
                          ) : (
                            <item.icon
                              className={`h-4 w-4 flex-shrink-0 ${
                                isSelected ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-tertiary)]'
                              }`}
                            />
                          )}
                          <span className="truncate text-sm font-medium">{item.display}</span>
                          {item.type === 'history' && describeSearchHistoryContext(item.historyItem) && (
                            <span className="truncate text-[11px] text-[var(--od-text-tertiary)]">
                              {describeSearchHistoryContext(item.historyItem)}
                            </span>
                          )}
                        </div>
                      )}

                      {item.type === 'history' && (
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            onRemoveHistory?.(item.historyItem);
                          }}
                          className="rounded p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-[var(--od-card-hover)]"
                        >
                          <X className="h-3.5 w-3.5 text-[var(--od-text-tertiary)]" />
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
      )}

      <div className="flex items-center justify-between border-t border-[var(--od-border)] bg-[var(--od-bg-tertiary)]/50 p-od-sm text-od-xs text-[var(--od-text-tertiary)]">
        <div>{preferenceAware ? '智能搜索导航 · 建议已按偏好收束' : '智能搜索导航'}</div>
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
    </>
  );

  if (embedded) {
    return (
      <div ref={dropdownRef} className="w-full">
        {content}
      </div>
    );
  }

  return (
    <motion.div
      ref={dropdownRef}
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="od-floating-panel-solid absolute right-0 top-full z-50 mt-od-sm w-full origin-top overflow-hidden rounded-lg border border-[var(--od-border-strong)] shadow-2xl sm:w-[560px]"
    >
      {content}
    </motion.div>
  );
}
