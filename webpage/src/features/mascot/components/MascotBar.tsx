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
        <div className="fixed bottom-6 left-64 z-40 flex items-end gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
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
            <div className="relative mb-4 max-w-md">
                <div className="relative rounded-2xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-6 py-3 shadow-xl">
                    <p className="text-sm font-medium text-[var(--od-text-primary)] whitespace-nowrap">
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

                {/* Bubble Tail */}
                <div className="absolute -left-2 bottom-4 h-4 w-4 rotate-45 border-b border-l border-[var(--od-border)] bg-[var(--od-bg-secondary)]" />
            </div>
        </div>
    );
}

