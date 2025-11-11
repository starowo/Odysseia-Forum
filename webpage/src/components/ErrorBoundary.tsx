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
        <div className="flex min-h-screen items-center justify-center bg-[#1e1f22] p-4">
          <div className="w-full max-w-2xl">
            <div className="rounded-2xl bg-[#2b2d31] p-8 shadow-2xl border border-[#3f4147]">
              {/* 错误图标 */}
              <div className="mb-6 flex justify-center">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#f23f42]/10">
                  <AlertTriangle className="h-10 w-10 text-[#f23f42]" />
                </div>
              </div>

              {/* 错误标题 */}
              <h1 className="mb-4 text-center text-2xl font-bold text-[#f2f3f5]">
                哎呀，出错了！
              </h1>

              {/* 错误描述 */}
              <p className="mb-6 text-center text-[#b5bac1]">
                应用遇到了一个意外错误。我们已经记录了这个问题，请稍后再试。
              </p>

              {/* 错误详情（开发环境） */}
              {import.meta.env.DEV && this.state.error && (
                <div className="mb-6 rounded-lg bg-[#1e1f22] p-4 border border-[#3f4147]">
                  <p className="mb-2 text-sm font-semibold text-[#f23f42]">
                    错误信息:
                  </p>
                  <pre className="overflow-x-auto text-xs text-[#949ba4]">
                    {this.state.error.toString()}
                  </pre>
                  {this.state.errorInfo && (
                    <>
                      <p className="mb-2 mt-4 text-sm font-semibold text-[#f23f42]">
                        组件堆栈:
                      </p>
                      <pre className="overflow-x-auto text-xs text-[#949ba4]">
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
                  className="flex items-center justify-center gap-2 rounded-lg bg-[#5865f2] px-6 py-3 text-sm font-medium text-white transition-all hover:bg-[#4752c4] hover:scale-105"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>重试</span>
                </button>
                <button
                  onClick={this.handleGoHome}
                  className="flex items-center justify-center gap-2 rounded-lg bg-[#2b2d31] px-6 py-3 text-sm font-medium text-[#f2f3f5] transition-all hover:bg-[#35373c] border border-[#3f4147]"
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
