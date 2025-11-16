import { useMemo } from 'react';

interface MarkdownTextProps {
  text: string;
}

/**
 * 极轻量级 Markdown 渲染：
 * - **bold**
 * - `code`
 * - [label](url)
 * - # / ## 标题
 * - > 引用
 * - 换行 => <br/>
 *
 * 不依赖额外库，只用于展示首条消息摘要。
 */
function parseMarkdown(text: string): string {
  if (!text) return '';

  let html = text
    // 先做最基本的转义，防止插入任意 HTML
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>');

  // 粗体 **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // 行内代码 `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 链接 [label](url)
  html = html.replace(
    /\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );

  // 引用 > text
  html = html.replace(/^>\s?(.*)$/gim, '<blockquote>$1</blockquote>');

  // 标题 # / ##
  html = html
    .replace(/^# (.*)$/gim, '<h1>$1</h1>')
    .replace(/^## (.*)$/gim, '<h2>$1</h2>');

  // 换行
  html = html.replace(/\n/g, '<br />');

  return html;
}

export function MarkdownText({ text }: MarkdownTextProps) {
  const html = useMemo(() => parseMarkdown(text), [text]);

  return (
    <div
      className="od-md text-[var(--od-text-secondary)] text-xs sm:text-sm leading-relaxed"
      // 内容来源为后端首条消息摘要，且经过基础转义，只保留我们允许的 markdown 片段
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}