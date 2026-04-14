import { MASCOT_IMAGES } from '../assets';
import { X } from 'lucide-react';
import { useMascotStore } from '../store/mascotStore';
import { useEffect, useState } from 'react';

export function MascotBar() {
    const emotion = useMascotStore((state) => state.emotion);
    const message = useMascotStore((state) => state.message);
    const isVisible = useMascotStore((state) => state.isVisible);
    const setVisible = useMascotStore((state) => state.setVisible);
    const reset = useMascotStore((state) => state.reset);
    const imageSrc = MASCOT_IMAGES[emotion] || MASCOT_IMAGES['hi'];
    const [imageLoaded, setImageLoaded] = useState(false);

    useEffect(() => {
        setImageLoaded(false);
        const preloadTargets = Array.from(new Set([MASCOT_IMAGES['hi'], imageSrc].filter(Boolean)));
        preloadTargets.forEach((src) => {
            const img = new Image();
            img.decoding = 'async';
            img.src = src;
        });
    }, [imageSrc]);

    // Simple interaction: reset to random idle message on click
    const handleMascotClick = () => {
        reset();
    };

    return (
        <div
            className={`pointer-events-none fixed bottom-20 left-1/2 z-40 flex -translate-x-1/2 flex-col-reverse items-center gap-4 transition-all duration-500 md:bottom-6 lg:left-[11.5rem] lg:translate-x-0 lg:flex-row lg:items-end ${
                isVisible
                    ? 'translate-y-0 opacity-100'
                    : 'pointer-events-none translate-y-6 opacity-0'
            }`}
        >
            {/* Mascot Image */}
            <div
                className="pointer-events-auto relative z-10 -mb-2 h-24 w-24 cursor-pointer transition-transform hover:scale-110 active:scale-95"
                onClick={handleMascotClick}
            >
                {!imageLoaded && (
                    <div className="absolute inset-0 animate-pulse rounded-full bg-[color-mix(in_srgb,var(--od-surface-shell)_80%,transparent)]" />
                )}
                <img
                    src={imageSrc}
                    alt="Mascot"
                    className={`h-full w-full object-contain drop-shadow-lg transition-opacity duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
                    loading="eager"
                    decoding="async"
                    onLoad={() => setImageLoaded(true)}
                    onError={(event) => {
                        const fallback = MASCOT_IMAGES['hi'];
                        if (fallback && event.currentTarget.src !== fallback) {
                            event.currentTarget.src = fallback;
                            return;
                        }
                        setImageLoaded(true);
                    }}
                />
            </div>

            {/* Dialogue Box */}
            <div className="pointer-events-auto relative mb-4 max-w-[300px] lg:max-w-md">
                <div className="relative overflow-hidden rounded-[1.35rem] border border-[color-mix(in_srgb,var(--od-border)_75%,transparent)] bg-[color-mix(in_srgb,var(--od-surface-floating)_88%,transparent)] px-4 py-3 shadow-[var(--od-shadow-floating)] backdrop-blur-md lg:px-5">
                    <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--od-accent)_10%,transparent),transparent_48%,color-mix(in_srgb,var(--od-text-primary)_5%,transparent))]" />
                    <p className="text-sm font-medium text-[var(--od-text-primary)]">
                        {message}
                    </p>

                    {/* Close Button */}
                    <button
                        onClick={() => setVisible(false)}
                        className="absolute -right-2 -top-2 rounded-full bg-[var(--od-bg-tertiary)] p-1 text-[var(--od-text-tertiary)] opacity-0 shadow-sm transition-all hover:bg-[var(--od-error)] hover:text-white hover:opacity-100"
                    >
                        <X size={12} />
                    </button>
                </div>

                {/* Bubble Tail - Mobile (Bottom Center) */}
                <div className="absolute -bottom-2 left-1/2 h-4 w-4 -translate-x-1/2 rotate-45 border-b border-r border-[var(--od-border)] bg-[var(--od-bg-secondary)] lg:hidden" />

                {/* Bubble Tail - Desktop (Left Side) */}
                <div className="absolute -left-2 bottom-4 hidden h-4 w-4 rotate-45 border-b border-l border-[var(--od-border)] bg-[var(--od-bg-secondary)] lg:block" />
            </div>
        </div>
    );
}
