import { useMemo } from 'react';

interface MarkdownTextProps {
  text: string;
}

/**
 * Discord风格 Markdown 渲染：
 * - **bold** / *italic* / ***bold italic***
 * - __underline__ / ~~strikethrough~~
 * - ||spoiler||
 * - # / ## / ### 标题
 * - [label](url) 和自动链接识别
 * - `code`
 * - > 引用
 * - 换行 => <br/>
 */
function parseMarkdown(text: string): string {
  if (!text) return '';

  // 基础HTML转义
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // === Discord特殊语法 ===

  // 1. Spoiler ||text|| - 需要特殊处理,渲染为自定义组件
  // 暂时用data-spoiler标记,后续用React组件替换
  html = html.replace(/\|\|(.+?)\|\|/g, '<span class="spoiler" data-spoiler="true">$1</span>');

  // 2. 下划线 __text__ (Discord特有,标准markdown是_italic_)
  html = html.replace(/__(.*?)__/g, '<u>$1</u>');

  // 3. 删除线 ~~text~~
  html = html.replace(/~~(.*?)~~/g, '<del>$1</del>');

  // 4. 粗斜体 ***text*** (必须在粗体和斜体之前)
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');

  // 5. 粗体 **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // 6. 斜体 *text* 或 _text_
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.*?)_/g, '<em>$1</em>');

  // 7. 行内代码 `code`
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

  // === 标题 (需要在行首) ===
  html = html
    .replace(/^### (.*)$/gim, '<h3 class="discord-h3">$1</h3>')
    .replace(/^## (.*)$/gim, '<h2 class="discord-h2">$1</h2>')
    .replace(/^# (.*)$/gim, '<h1 class="discord-h1">$1</h1>');

  // === 链接处理 ===

  // 1. Markdown链接 [label](url)
  html = html.replace(
    /\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="discord-link">$1</a>',
  );

  // 2. 自动识别URL (Discord会自动将URL转为链接)
  // 排除已经在<a>标签中的URL
  html = html.replace(
    /(?<!href=")(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer" class="discord-link">$1</a>',
  );

  // === 引用 ===
  html = html.replace(/^> (.*)$/gim, '<blockquote class="discord-quote">$1</blockquote>');

  // === 换行 ===
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