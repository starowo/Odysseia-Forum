import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { render } from '@/tests/test-utils';
import { SearchPage } from './index';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';

// Mock 子组件和动画以简化环境
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
  useAnimation: () => ({ start: vi.fn(), stop: vi.fn() }),
  useInView: () => [null, true],
}));

// Mock 搜索 URL 钩子，以便观察参数变化
vi.mock('@/features/search/hooks/useSearchParams', () => ({
  useSearchURLParams: vi.fn(),
}));

const DEFAULT_PARAMS = {
  query: '',
  channel: null,
  sortMethod: 'last_active_desc',
  includeTags: [],
  excludeTags: [],
  tagLogic: 'and',
  timeFrom: '',
  timeTo: '',
};

describe('SearchPage 交互测试', () => {
  const mockSetParams = vi.fn();
  const mockClearParams = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useSearchURLParams as any).mockReturnValue({
      params: DEFAULT_PARAMS,
      setParams: mockSetParams,
      clearParams: mockClearParams,
      hasActiveFilters: false,
    });
  });

  it('在搜索框输入文字并回车，应该触发 setParams', async () => {
    render(<SearchPage />);

    const input = screen.getByPlaceholderText(/搜索/i);
    fireEvent.change(input, { target: { value: '测试关键词' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(mockSetParams).toHaveBeenCalledWith({ query: '测试关键词' });
  });

  it('点击清空筛选按钮，应该触发 clearParams', async () => {
    // 模拟有活动筛选的状态
    (useSearchURLParams as any).mockReturnValue({
      params: { ...DEFAULT_PARAMS, query: '已有搜索' },
      setParams: mockSetParams,
      clearParams: mockClearParams,
      hasActiveFilters: true,
    });

    render(<SearchPage />);

    const clearButton = screen.getByText(/清空所有筛选条件/i);
    fireEvent.click(clearButton);

    expect(mockClearParams).toHaveBeenCalled();
  });
});

