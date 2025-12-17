import { LazyImage } from '@/components/common/LazyImage';
import { Image as ImageIcon } from 'lucide-react';

interface MultiImageGridProps {
    images: string[];
    alt: string;
    className?: string;
}

export function MultiImageGrid({ images, alt, className = '' }: MultiImageGridProps) {
    const count = images.length;

    if (count === 0) {
        return (
            <div className={`h-full w-full bg-gradient-to-br from-[var(--od-bg-secondary)] to-[var(--od-bg-tertiary)] ${className}`} />
        );
    }

    if (count === 1) {
        return (
            <div className={`relative h-full w-full overflow-hidden ${className}`}>
                <LazyImage
                    src={images[0]}
                    alt={alt}
                    className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                />
            </div>
        );
    }

    if (count === 2) {
        return (
            <div className={`grid h-full w-full grid-cols-2 gap-0.5 ${className}`}>
                {images.map((src, idx) => (
                    <div key={idx} className="relative h-full w-full overflow-hidden">
                        <LazyImage
                            src={src}
                            alt={`${alt} ${idx + 1}`}
                            className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                        />
                    </div>
                ))}
            </div>
        );
    }

    if (count === 3) {
        return (
            <div className={`grid h-full w-full grid-cols-[1.5fr_1fr] grid-rows-2 gap-0.5 ${className}`}>
                <div className="relative row-span-2 h-full w-full overflow-hidden">
                    <LazyImage
                        src={images[0]}
                        alt={`${alt} 1`}
                        className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                    />
                </div>
                <div className="relative h-full w-full overflow-hidden">
                    <LazyImage
                        src={images[1]}
                        alt={`${alt} 2`}
                        className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                    />
                </div>
                <div className="relative h-full w-full overflow-hidden">
                    <LazyImage
                        src={images[2]}
                        alt={`${alt} 3`}
                        className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                    />
                </div>
            </div>
        );
    }

    // 4 or more
    const displayImages = images.slice(0, 4);
    const remaining = count - 4;

    return (
        <div className={`grid h-full w-full grid-cols-2 grid-rows-2 gap-0.5 ${className}`}>
            {displayImages.map((src, idx) => (
                <div key={idx} className="relative h-full w-full overflow-hidden">
                    <LazyImage
                        src={src}
                        alt={`${alt} ${idx + 1}`}
                        className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                    />
                    {idx === 3 && remaining > 0 && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-xl font-bold text-white backdrop-blur-[2px]">
                            +{remaining}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
