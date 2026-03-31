interface HighlightTextProps {
  text: string;
  highlight?: string;
  className?: string;
}

export function HighlightText({ text, highlight, className = '' }: HighlightTextProps) {
  if (!highlight || !highlight.trim()) {
    return <span className={className}>{text}</span>;
  }

  try {
    // 转义特殊字符
    const escapedHighlight = highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const parts = text.split(new RegExp(`(${escapedHighlight})`, 'gi'));

    return (
      <span className={className}>
        {parts.map((part, index) =>
          part.toLowerCase() === highlight.toLowerCase() ? (
            <mark
              key={index}
              className="bg-[#5865f2]/30 text-[#00a8fc] rounded px-0.5 font-semibold"
            >
              {part}
            </mark>
          ) : (
            <span key={index}>{part}</span>
          )
        )}
      </span>
    );
  } catch (error) {
    // 如果正则表达式失败，返回原文本
    return <span className={className}>{text}</span>;
  }
}
