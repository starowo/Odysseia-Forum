
interface DiscordMarkdownTextProps {
  text: string;
  className?: string;
  truncateClassName?: string;
}

export function DiscordMarkdownText({ text, className = '', truncateClassName = '' }: DiscordMarkdownTextProps) {
  if (!text) return null;

  // 简易行内 Markdown 解析器
  // 匹配: 链接 [text](url) | 粗体 **text** | 行内代码 `code`
  const regex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`/g;
  const parts = [];
  let lastIndex = 0;
  
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }

    if (match[1] && match[2]) {
      // 匹配到链接
      parts.push({ type: 'link', text: match[1], url: match[2] });
    } else if (match[3]) {
      // 匹配到粗体
      parts.push({ type: 'bold', content: match[3] });
    } else if (match[4]) {
      // 匹配到代码块
      parts.push({ type: 'code', content: match[4] });
    }

    lastIndex = regex.lastIndex;
  }
  
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  return (
    <span className={`inline ${className} ${truncateClassName}`}>
      {parts.map((part, index) => {
        if (part.type === 'link') {
          return (
            <a
              key={index}
              href={part.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-[var(--od-accent)] hover:underline"
              onClick={(e) => e.stopPropagation()}
              title={part.url}
            >
              {part.text}
            </a>
          );
        }
        if (part.type === 'bold') {
          return <strong key={index} className="font-bold text-[var(--od-text-primary)]">{part.content}</strong>;
        }
        if (part.type === 'code') {
          return <code key={index} className="rounded-md bg-[var(--od-surface-shelled)] px-1 py-0.5 font-mono text-[0.85em] text-[var(--od-text-primary)]">{part.content}</code>;
        }
        return <span key={index}>{part.content}</span>;
      })}
    </span>
  );
}
