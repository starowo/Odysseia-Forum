import { useState } from 'react';

interface SpoilerProps {
    children: React.ReactNode;
}

/**
 * Discord风格的遮罩文本组件
 * 默认显示为黑色遮罩,点击后显示内容
 */
export function Spoiler({ children }: SpoilerProps) {
    const [revealed, setRevealed] = useState(false);

    return (
        <span
            className={`inline-block rounded px-1 transition-all cursor-pointer ${revealed
                    ? 'bg-[#3f3f46] text-[var(--od-text-primary)]'
                    : 'bg-[#2d2d30] text-transparent select-none hover:bg-[#3a3a3d]'
                }`}
            onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setRevealed(true);
            }}
            title={revealed ? '' : '点击查看隐藏内容'}
        >
            {children}
        </span>
    );
}
