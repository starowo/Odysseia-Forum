import { useState, useEffect } from 'react';
import { X, ChevronRight } from 'lucide-react';
import { MascotEmotion, MASCOT_IMAGES } from '../assets';

interface MascotDialogProps {
    emotion?: MascotEmotion;
    title?: string;
    children: React.ReactNode; // Content of the dialogue
    visible?: boolean;
    onClose?: () => void;
    showCloseButton?: boolean;
    actionLabel?: string;
    onAction?: () => void;
    className?: string;
}

export function MascotDialog({
    emotion = 'hi',
    title,
    children,
    visible = true,
    onClose,
    showCloseButton = true,
    actionLabel,
    onAction,
    className = '',
}: MascotDialogProps) {
    const [isRendered, setIsRendered] = useState(visible);

    useEffect(() => {
        if (visible) {
            setIsRendered(true);
        } else {
            const timer = setTimeout(() => setIsRendered(false), 300); // Wait for exit animation
            return () => clearTimeout(timer);
        }
    }, [visible]);

    if (!isRendered) return null;

    const imageSrc = MASCOT_IMAGES[emotion];

    return (
        <div
            className={`fixed inset-0 z-[100] flex items-center justify-center p-4 transition-all duration-300 ${visible ? 'bg-black/60 backdrop-blur-sm opacity-100' : 'bg-black/0 backdrop-blur-none opacity-0 pointer-events-none'
                }`}
            onClick={onClose}
        >
            <div
                className={`relative flex w-full max-w-2xl flex-col items-center md:flex-row md:items-end gap-4 transition-all duration-500 ${visible ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-8 opacity-0 scale-95'
                    } ${className}`}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Character Image - Galgame Style (Left) */}
                <div className="relative z-10 -mb-8 md:-mr-12 md:mb-0 flex-shrink-0">
                    <img
                        src={imageSrc}
                        alt={`Mascot ${emotion}`}
                        className="h-64 w-auto object-contain drop-shadow-2xl md:h-80 transition-transform duration-300 hover:scale-105 animate-in slide-in-from-bottom-8 fade-in duration-700"
                    />
                </div>

                {/* Dialogue Box (Right/Bottom) */}
                <div className="relative flex-1 w-full min-w-0">
                    <div className="relative overflow-hidden rounded-2xl border-2 border-[var(--od-accent)] bg-[var(--od-card)] p-6 shadow-2xl backdrop-blur-md animate-in slide-in-from-right-8 fade-in duration-500 delay-100">
                        {/* Decorative Corner */}
                        <div className="absolute -right-2 -top-2 h-8 w-8 rotate-45 bg-[var(--od-accent)]/20" />

                        {/* Header */}
                        <div className="mb-2 flex items-center justify-between">
                            {title && (
                                <h3 className="text-lg font-bold text-[var(--od-accent)] flex items-center gap-2">
                                    <span className="inline-block h-2 w-2 rounded-full bg-[var(--od-accent)] animate-pulse" />
                                    {title}
                                </h3>
                            )}
                            {showCloseButton && onClose && (
                                <button
                                    onClick={onClose}
                                    className="rounded-full p-1 text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)] transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            )}
                        </div>

                        {/* Content */}
                        <div className="text-[var(--od-text-primary)] leading-relaxed text-sm md:text-base">
                            {children}
                        </div>

                        {/* Action Button */}
                        {(actionLabel || onAction) && (
                            <div className="mt-4 flex justify-end">
                                <button
                                    onClick={onAction || onClose}
                                    className="group flex items-center gap-1 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-bold text-white shadow-lg transition-all hover:bg-[var(--od-accent-hover)] hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0"
                                >
                                    {actionLabel || '继续'}
                                    <ChevronRight size={16} className="transition-transform group-hover:translate-x-1" />
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
