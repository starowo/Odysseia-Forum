import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MarkdownText } from './MarkdownText';

describe('MarkdownText', () => {
  const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

  beforeEach(() => {
    openSpy.mockClear();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('将危险协议渲染为普通文本而非链接', () => {
    render(<MarkdownText text={'[danger](javascript:alert(1))'} />);
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByText('[danger](javascript:alert(1))')).toBeInTheDocument();
  });

  it('点击 Discord 链接时不弹警告', () => {
    render(<MarkdownText text={'https://discord.com/channels/1/2/3'} />);
    const link = screen.getByRole('link');

    fireEvent.click(link);

    expect(screen.queryByRole('dialog')).toBeNull();
    expect(openSpy).not.toHaveBeenCalled();
  });

  it('点击非 Discord 链接时显示警告并在确认后打开', () => {
    render(<MarkdownText text={'https://example.com/post'} />);
    const link = screen.getByRole('link');

    fireEvent.click(link);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('example.com')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '继续前往' }));

    expect(openSpy).toHaveBeenCalledWith('https://example.com/post', '_blank', 'noopener,noreferrer');
  });
});
