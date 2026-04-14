import type { CSSProperties, ReactNode } from 'react';
import { toast, type ExternalToast } from 'sonner';

import { MASCOT_IMAGES, type MascotEmotion } from '@/features/mascot/assets';
import {
  resolveErrorMascotMessage,
  type MascotErrorType,
  type ResolvedMascotMessage,
} from '@/features/mascot/lib/messageResolver';

interface MascotToastOptions extends ExternalToast {
  emotion?: MascotEmotion;
  message?: ReactNode;
  title?: ReactNode;
  eyebrow?: ReactNode;
  actionLabel?: ReactNode;
  onAction?: () => void;
  cancelLabel?: ReactNode;
  onCancel?: () => void;
}

const DEFAULT_TOAST_DURATION = 5200;

const mascotToastStyle: CSSProperties = {
  padding: 0,
  border: 'none',
  background: 'transparent',
  boxShadow: 'none',
  width: 'min(26rem, calc(100vw - 2rem))',
};

export function showMascotToast({
  emotion = 'hi',
  message,
  title = '类脑娘小提示',
  eyebrow = 'Mascot Signal',
  actionLabel,
  onAction,
  cancelLabel,
  onCancel,
  duration = DEFAULT_TOAST_DURATION,
  className,
  ...options
}: MascotToastOptions) {
  return toast.custom(
    (id) => (
      <MascotToastCard
        id={id}
        emotion={emotion}
        title={title}
        eyebrow={eyebrow}
        message={message}
        actionLabel={actionLabel}
        onAction={onAction}
        cancelLabel={cancelLabel}
        onCancel={onCancel}
      />
    ),
    {
      ...options,
      className,
      duration,
      dismissible: true,
      unstyled: true,
      style: mascotToastStyle,
    },
  );
}

export function showMascotErrorToast(type: MascotErrorType = 'generic', options?: MascotToastOptions) {
  const resolved = resolveErrorMascotMessage(type);
  return showResolvedMascotToast(resolved, {
    eyebrow: type === 'network' ? 'Network Trouble' : type === 'notFound' ? 'Lost Route' : 'System Notice',
    title: type === 'network' ? '连接似乎不太顺' : type === 'notFound' ? '这里暂时没有路' : '出了点小状况',
    ...options,
  });
}

export function showResolvedMascotToast(
  resolved: ResolvedMascotMessage,
  options?: Omit<MascotToastOptions, 'emotion' | 'message'>,
) {
  return showMascotToast({
    ...options,
    emotion: resolved.emotion,
    message: resolved.message,
  });
}

interface MascotToastCardProps {
  id: string | number;
  emotion: MascotEmotion;
  title: ReactNode;
  eyebrow: ReactNode;
  message: ReactNode;
  actionLabel?: ReactNode;
  onAction?: () => void;
  cancelLabel?: ReactNode;
  onCancel?: () => void;
}

function MascotToastCard({
  id,
  emotion,
  title,
  eyebrow,
  message,
  actionLabel,
  onAction,
  cancelLabel,
  onCancel,
}: MascotToastCardProps) {
  const imageSrc = MASCOT_IMAGES[emotion] || MASCOT_IMAGES.hi;

  return (
    <div className="od-mascot-toast animate-in slide-in-from-top-4 fade-in duration-300">
      <div className="od-mascot-toast-figure">
        <img src={imageSrc} alt="Mascot" className="od-mascot-toast-image" />
      </div>

      <div className="od-mascot-toast-body">
        <div className="od-mascot-toast-eyebrow">{eyebrow}</div>
        <p className="od-mascot-toast-title">{title}</p>
        <div className="od-mascot-toast-copy">{message}</div>
        {(actionLabel || cancelLabel) && (
          <div className="od-mascot-toast-actions">
            {cancelLabel && (
              <button
                type="button"
                className="od-mascot-toast-button od-mascot-toast-button-secondary"
                onClick={() => {
                  onCancel?.();
                  toast.dismiss(id);
                }}
              >
                {cancelLabel}
              </button>
            )}
            {actionLabel && (
              <button
                type="button"
                className="od-mascot-toast-button od-mascot-toast-button-primary"
                onClick={() => {
                  onAction?.();
                  toast.dismiss(id);
                }}
              >
                {actionLabel}
              </button>
            )}
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => toast.dismiss(id)}
        className="od-mascot-toast-close"
        aria-label="关闭提示"
      >
        ×
      </button>
    </div>
  );
}
