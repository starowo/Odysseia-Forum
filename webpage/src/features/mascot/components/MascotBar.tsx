import { MASCOT_IMAGES } from '../assets';
import { X } from 'lucide-react';
import { useMascotStore } from '../store/mascotStore';

export function MascotBar() {
    const { emotion, message, isVisible, setVisible, reset } = useMascotStore();

    // Simple interaction: reset to random idle message on click
    const handleMascotClick = () => {
        reset();
    };

    if (!isVisible) return null;

    return (
        <div className="fixed bottom-6 z-40 flex flex-col-reverse items-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500 left-1/2 -translate-x-1/2 lg:left-64 lg:translate-x-0 lg:flex-row lg:items-end">
            {/* Mascot Image */}
            <div
                className="relative z-10 -mb-2 h-24 w-24 cursor-pointer transition-transform hover:scale-110 active:scale-95"
                onClick={handleMascotClick}
            >
                <img
                    src={MASCOT_IMAGES[emotion] || MASCOT_IMAGES['hi']}
                    alt="Mascot"
                    className="h-full w-full object-contain drop-shadow-lg"
                />
            </div>

            {/* Dialogue Box */}
            <div className="relative mb-4 max-w-[280px] lg:max-w-md">
                <div className="relative rounded-2xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-4 py-3 shadow-xl lg:px-6">
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
