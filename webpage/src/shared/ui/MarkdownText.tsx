import { useMemo, useState } from 'react';
import { getUrlSafetyInfo, parseHttpUrl } from '@/shared/lib/urlSafety';
import { ExternalLinkWarningDialog } from '@/shared/ui/ExternalLinkWarningDialog';

interface MarkdownTextProps {
  text: string;
}

interface PendingExternalLink {
  href: string;
  hostname: string;
}

function decodeHtmlEntities(value: string): string {
  return value
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function escapeHtmlAttribute(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function buildSafeAnchor(label: string, rawUrl: string): string {
  const parsedUrl = parseHttpUrl(decodeHtmlEntities(rawUrl));
  if (!parsedUrl) {
    return label;
  }

  const href = escapeHtmlAttribute(parsedUrl.toString());
  return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="discord-link">${label}</a>`;
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

  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  html = html.replace(/\|\|(.+?)\|\|/g, '<span class="spoiler" data-spoiler="true">$1</span>');
  html = html.replace(/__(.*?)__/g, '<u>$1</u>');
  html = html.replace(/~~(.*?)~~/g, '<del>$1</del>');
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.*?)_/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

  html = html
    .replace(/^### (.*)$/gim, '<h3 class="discord-h3">$1</h3>')
    .replace(/^## (.*)$/gim, '<h2 class="discord-h2">$1</h2>')
    .replace(/^# (.*)$/gim, '<h1 class="discord-h1">$1</h1>');

  html = html.replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g, (_match, label: string, url: string) => {
    return buildSafeAnchor(label, url);
  });

  html = html.replace(/(?<!href=")(https?:\/\/[^\s<]+)/g, (rawUrl: string) => {
    return buildSafeAnchor(rawUrl, rawUrl);
  });

  html = html.replace(/^> (.*)$/gim, '<blockquote class="discord-quote">$1</blockquote>');
  html = html.replace(/\n/g, '<br />');

  return html;
}

export function MarkdownText({ text }: MarkdownTextProps) {
  const html = useMemo(() => parseMarkdown(text), [text]);
  const [pendingExternalLink, setPendingExternalLink] = useState<PendingExternalLink | null>(null);

  const handleClickCapture = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    const anchor = target.closest('a');
    if (!(anchor instanceof HTMLAnchorElement)) return;

    const info = getUrlSafetyInfo(anchor.href);
    if (!info) {
      event.preventDefault();
      return;
    }

    if (!info.requiresExternalWarning) {
      return;
    }

    event.preventDefault();
    setPendingExternalLink({ href: info.href, hostname: info.hostname });
  };

  const handleConfirmExternalLink = () => {
    if (!pendingExternalLink) return;

    window.open(pendingExternalLink.href, '_blank', 'noopener,noreferrer');
    setPendingExternalLink(null);
  };

  return (
    <>
      <div
        className="od-md text-[var(--od-text-secondary)] text-xs sm:text-sm leading-relaxed"
        onClickCapture={handleClickCapture}
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {pendingExternalLink && (
        <ExternalLinkWarningDialog
          hostname={pendingExternalLink.hostname}
          href={pendingExternalLink.href}
          onCancel={() => setPendingExternalLink(null)}
          onConfirm={handleConfirmExternalLink}
        />
      )}
    </>
  );
}
