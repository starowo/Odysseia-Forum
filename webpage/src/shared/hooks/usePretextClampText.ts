import { layoutWithLines, prepareWithSegments } from '@chenglou/pretext';
import { useCallback, useEffect, useRef, useState } from 'react';

interface UsePretextClampTextOptions {
  maxLines: number;
  enabled?: boolean;
}

function buildCanvasFont(style: CSSStyleDeclaration) {
  const fontStyle = style.fontStyle || 'normal';
  const fontWeight = style.fontWeight || '400';
  const fontSize = style.fontSize || '14px';
  const fontFamily = style.fontFamily || 'Inter';

  return `${fontStyle} ${fontWeight} ${fontSize} ${fontFamily}`;
}

function resolveLineHeight(style: CSSStyleDeclaration) {
  const parsed = Number.parseFloat(style.lineHeight);
  if (Number.isFinite(parsed)) return parsed;

  const fontSize = Number.parseFloat(style.fontSize || '14');
  return Number.isFinite(fontSize) ? fontSize * 1.4 : 20;
}

export function usePretextClampText<T extends HTMLElement = HTMLElement>(
  text: string,
  options: UsePretextClampTextOptions,
) {
  const { maxLines, enabled = true } = options;
  const measureRef = useRef<T | null>(null);
  const [clampedText, setClampedText] = useState(text);

  const recompute = useCallback(() => {
    if (!enabled || !text) {
      setClampedText(text);
      return;
    }

    const element = measureRef.current;
    if (!element) {
      setClampedText(text);
      return;
    }

    const maxWidth = element.clientWidth;
    if (!maxWidth || maxWidth <= 0) {
      setClampedText(text);
      return;
    }

    try {
      const style = window.getComputedStyle(element);
      const font = buildCanvasFont(style);
      const lineHeight = resolveLineHeight(style);
      const prepared = prepareWithSegments(text, font, { whiteSpace: 'normal' });
      const laidOut = layoutWithLines(prepared, maxWidth, lineHeight);

      if (laidOut.lineCount <= maxLines) {
        setClampedText((prev) => (prev === text ? prev : text));
        return;
      }

      const visible = laidOut.lines
        .slice(0, maxLines)
        .map((line) => line.text)
        .join('')
        .trimEnd();
      const next = visible ? `${visible}…` : text;

      setClampedText((prev) => (prev === next ? prev : next));
    } catch {
      setClampedText((prev) => (prev === text ? prev : text));
    }
  }, [enabled, maxLines, text]);

  useEffect(() => {
    recompute();
  }, [recompute]);

  useEffect(() => {
    if (!enabled) return;

    const element = measureRef.current;
    if (!element) return;

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(() => {
        recompute();
      });
      observer.observe(element);
      return () => observer.disconnect();
    }

    const onResize = () => recompute();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [enabled, recompute]);

  return {
    measureRef,
    clampedText,
  };
}
