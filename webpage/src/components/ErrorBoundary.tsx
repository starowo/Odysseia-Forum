import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义 fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认错误 UI
      return (
        <div className="flex min-h-screen items-center justify-center bg-[var(--od-bg)] p-4">
          <div className="w-full max-w-2xl">
            <div className="rounded-2xl border border-[var(--od-border-strong)] bg-[var(--od-card)] p-8 shadow-2xl">
              {/* 错误图标 */}
              <div className="mb-6 flex justify-center">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[color-mix(in_oklab,var(--od-error)_12%,transparent)]">
                  <AlertTriangle className="h-10 w-10 text-[var(--od-error)]" />
                </div>
              </div>

              {/* 错误标题 */}
              <h1 className="mb-4 text-center text-2xl font-bold text-[var(--od-text-primary)]">
                哎呀，出错了！
              </h1>

              {/* 错误描述 */}
              <p className="mb-6 text-center text-[var(--od-text-secondary)]">
                应用遇到了一个意外错误。我们已经记录了这个问题，请稍后再试。
              </p>

              {/* 错误详情（开发环境） */}
              {import.meta.env.DEV && this.state.error && (
                <div className="mb-6 rounded-lg border border-[var(--od-border-strong)] bg-[var(--od-bg-tertiary)] p-4">
                  <p className="mb-2 text-sm font-semibold text-[var(--od-error)]">
                    错误信息:
                  </p>
                  <pre className="overflow-x-auto text-xs text-[var(--od-text-tertiary)]">
                    {this.state.error.toString()}
                  </pre>
                  {this.state.errorInfo && (
                    <>
                      <p className="mb-2 mt-4 text-sm font-semibold text-[var(--od-error)]">
                        组件堆栈:
                      </p>
                      <pre className="overflow-x-auto text-xs text-[var(--od-text-tertiary)]">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
                <button
                  onClick={this.handleReset}
                  className="flex items-center justify-center gap-2 rounded-lg bg-[var(--od-accent)] px-6 py-3 text-sm font-medium text-white transition-all hover:scale-105 hover:bg-[var(--od-accent-hover)]"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>重试</span>
                </button>
                <button
                  onClick={this.handleGoHome}
                  className="flex items-center justify-center gap-2 rounded-lg border border-[var(--od-border-strong)] bg-[var(--od-bg-secondary)] px-6 py-3 text-sm font-medium text-[var(--od-text-primary)] transition-all hover:bg-[var(--od-bg-tertiary)]"
                >
                  <Home className="h-4 w-4" />
                  <span>返回首页</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
