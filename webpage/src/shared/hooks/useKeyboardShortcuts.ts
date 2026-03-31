import { useEffect } from 'react';

interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  alt?: boolean;
  callback: () => void;
  description?: string;
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;

        // 对于 Ctrl/Cmd + K 这样的组合，需要特殊处理
        const isModifierKey = shortcut.ctrl || shortcut.meta;
        const modifierPressed = event.ctrlKey || event.metaKey;

        if (isModifierKey) {
          if (
            event.key.toLowerCase() === shortcut.key.toLowerCase() &&
            modifierPressed &&
            (shortcut.shift ? event.shiftKey : !event.shiftKey) &&
            (shortcut.alt ? event.altKey : !event.altKey)
          ) {
            event.preventDefault();
            shortcut.callback();
            return;
          }
        } else {
          // 非修饰键的情况
          if (
            event.key === shortcut.key &&
            !event.ctrlKey &&
            !event.metaKey &&
            shiftMatch &&
            altMatch
          ) {
            // 确保不在输入框中
            const target = event.target as HTMLElement;
            if (
              target.tagName === 'INPUT' ||
              target.tagName === 'TEXTAREA' ||
              target.isContentEditable
            ) {
              return;
            }
            event.preventDefault();
            shortcut.callback();
            return;
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

// 快捷键帮助面板数据
export const defaultShortcuts = [
  { key: 'K', ctrl: true, meta: true, description: '聚焦搜索框' },
  { key: 'Escape', description: '清空搜索' },
  { key: '/', description: '快速搜索' },
  { key: '?', shift: true, description: '显示快捷键帮助' },
];
