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
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);

    useEffect(() => {
        if (visible) {
            setIsRendered(true);
        } else {
            const timer = setTimeout(() => setIsRendered(false), 300); // Wait for exit animation
            return () => clearTimeout(timer);
        }
    }, [visible]);

    const imageSrc = MASCOT_IMAGES[emotion] || MASCOT_IMAGES['hi'];
    const fallbackImageSrc = MASCOT_IMAGES['hi'] || imageSrc;

    useEffect(() => {
        setImageLoaded(false);
        setImageError(false);
    }, [imageSrc]);

    useEffect(() => {
        const preloadTargets = Array.from(new Set([imageSrc, fallbackImageSrc].filter(Boolean)));
        preloadTargets.forEach((src) => {
            const img = new Image();
            img.decoding = 'async';
            img.src = src;
        });
    }, [imageSrc, fallbackImageSrc]);

    if (!isRendered) return null;

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
                    {!imageLoaded && (
                        <div className="absolute inset-0 flex items-center justify-center rounded-[1.5rem] bg-white/8 backdrop-blur-sm">
                            <div className="h-32 w-24 animate-pulse rounded-[1.2rem] bg-white/10 md:h-56 md:w-40" />
                        </div>
                    )}
                    <img
                        src={imageError ? fallbackImageSrc : imageSrc}
                        alt={`Mascot ${emotion}`}
                        className={`h-48 w-auto object-contain drop-shadow-2xl transition-all duration-500 hover:scale-105 md:h-80 ${
                            imageLoaded ? 'opacity-100' : 'opacity-0'
                        } animate-in slide-in-from-bottom-8 fade-in duration-700`}
                        loading="eager"
                        decoding="async"
                        onLoad={() => {
                            setImageLoaded(true);
                            setImageError(false);
                        }}
                        onError={() => {
                            if (!imageError && fallbackImageSrc && fallbackImageSrc !== imageSrc) {
                                setImageError(true);
                                return;
                            }
                            setImageLoaded(true);
                        }}
                    />
                </div>

                {/* Dialogue Box (Right/Bottom) */}
                <div className="relative flex-1 w-full min-w-0">
                    <div className="relative flex flex-col gap-3 p-4 md:p-6 animate-in slide-in-from-right-8 fade-in duration-500 delay-100">
                        {/* Header */}
                        <div className="mb-2 flex items-center justify-between">
                            {title && (
                                <h3 className="text-xl md:text-2xl font-black text-white flex items-center gap-2 drop-shadow-md">
                                    <span className="inline-block h-2 w-2 rounded-full bg-[var(--od-accent)] animate-pulse shadow-[0_0_8px_var(--od-accent)]" />
                                    {title}
                                </h3>
                            )}
                            {showCloseButton && onClose && (
                                <button
                                    onClick={onClose}
                                    className="rounded-full p-2 text-white/50 hover:bg-white/10 hover:text-white transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            )}
                        </div>

                        {/* Content */}
                        <div className="text-white/90 leading-relaxed text-sm md:text-lg font-medium drop-shadow-sm">
                            {children}
                        </div>

                        {/* Action Button */}
                        {(actionLabel || onAction) && (
                            <div className="mt-6 flex justify-start">
                                <button
                                    onClick={onAction || onClose}
                                    className="group flex items-center gap-2 rounded-full border border-white/20 bg-white/10 backdrop-blur-md px-6 py-3 text-sm md:text-base font-bold text-white transition-all hover:bg-white/20 hover:border-white/40 hover:-translate-y-0.5 active:translate-y-0"
                                >
                                    {actionLabel || '继续'}
                                    <ChevronRight size={18} className="transition-transform group-hover:translate-x-1" />
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
