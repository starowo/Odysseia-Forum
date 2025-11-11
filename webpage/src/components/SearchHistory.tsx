import { History, X, Clock } from 'lucide-react';
import { getSearchHistory, removeSearchHistory, clearSearchHistory } from '@/lib/searchHistory';
import { useState, useEffect, useRef } from 'react';

interface SearchHistoryDropdownProps {
  isOpen: boolean;
  onSelectHistory: (query: string) => void;
  onClose: () => void;
  inputRef?: React.RefObject<HTMLInputElement>;
}

export function SearchHistoryDropdown({ 
  isOpen, 
  onSelectHistory, 
  onClose,
  inputRef 
}: SearchHistoryDropdownProps) {
  const [history, setHistory] = useState(getSearchHistory());
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 监听 storage 事件，当其他标签页更新历史时同步
    const handleStorageChange = () => {
      setHistory(getSearchHistory());
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  useEffect(() => {
    // 点击外部关闭下拉框
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

  const handleSelect = (query: string) => {
    onSelectHistory(query);
    onClose();
  };

  if (!isOpen || history.length === 0) {
    return null;
  }

  return (
    <div
      ref={dropdownRef}
      className="absolute left-0 right-0 top-full z-50 mt-2 rounded-lg bg-[#2b2d31] shadow-2xl border border-[#3f4147] animate-in fade-in slide-in-from-top-2 duration-200"
    >
      {/* 标题栏 */}
      <div className="flex items-center justify-between border-b border-[#3f4147] px-4 py-3">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-[#949ba4]" />
          <span className="text-sm font-semibold text-[#f2f3f5]">搜索历史</span>
        </div>
        <button
          onClick={handleClearAll}
          className="text-xs text-[#949ba4] transition-colors hover:text-[#f2f3f5]"
        >
          清空
        </button>
      </div>

      {/* 历史记录列表 */}
      <div className="max-h-[300px] overflow-y-auto">
        {history.map((item) => (
          <button
            key={item.timestamp}
            onClick={() => handleSelect(item.query)}
            className="group flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-[#35373c]"
          >
            <Clock className="h-4 w-4 flex-shrink-0 text-[#949ba4]" />
            <span className="flex-1 truncate text-sm text-[#e3e5e8]">
              {item.query}
            </span>
            <button
              onClick={(e) => handleRemove(item.query, e)}
              className="flex-shrink-0 rounded p-1 opacity-0 transition-all hover:bg-[#4e5058] group-hover:opacity-100"
              title="删除"
            >
              <X className="h-3.5 w-3.5 text-[#949ba4]" />
            </button>
          </button>
        ))}
      </div>
    </div>
  );
}
