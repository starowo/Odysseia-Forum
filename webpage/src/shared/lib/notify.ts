import axios from 'axios';
import { toast, type ExternalToast } from 'sonner';

interface NotifyMessageOptions extends ExternalToast {
  description?: string;
}

const DEFAULT_DURATION = 3600;
const DEFAULT_ERROR_DURATION = 4600;

export function notifySuccess(message: string, options?: NotifyMessageOptions) {
  return toast.success(message, {
    duration: DEFAULT_DURATION,
    ...options,
  });
}

export function notifyInfo(message: string, options?: NotifyMessageOptions) {
  return toast.info(message, {
    duration: DEFAULT_DURATION,
    ...options,
  });
}

export function notifyError(message: string, options?: NotifyMessageOptions) {
  return toast.error(message, {
    duration: DEFAULT_ERROR_DURATION,
    ...options,
  });
}

export function extractErrorMessage(error: unknown, fallback = '操作未完成，请稍后再试') {
  if (axios.isAxiosError(error)) {
    const responseMessage =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.response?.data?.error;

    if (typeof responseMessage === 'string' && responseMessage.trim()) {
      return responseMessage.trim();
    }

    if (error.code === 'ECONNABORTED') {
      return '请求超时，请稍后重试';
    }

    if (!error.response) {
      return '网络连接异常，请检查网络后重试';
    }

    if (error.response.status === 401) {
      return '登录状态已失效，请重新登录';
    }

    if (error.response.status === 403) {
      return '当前没有执行这个操作的权限';
    }

    if (error.response.status === 404) {
      return '目标内容不存在或已被移除';
    }

    if (error.response.status >= 500) {
      return '服务器暂时开小差了，请稍后再试';
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }

  return fallback;
}
