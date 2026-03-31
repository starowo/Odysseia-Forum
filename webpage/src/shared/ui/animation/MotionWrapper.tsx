import { motion, HTMLMotionProps } from 'framer-motion';
import { springs } from './variants';

interface MotionWrapperProps extends HTMLMotionProps<"div"> {
    children: React.ReactNode;
    scale?: number; // 悬停时的缩放比例
    tapScale?: number; // 点击时的缩放比例
    y?: number; // 悬停时的垂直位移
    className?: string;
    as?: React.ElementType; // 允许渲染为其他标签，如 'article', 'button'
}

export function MotionWrapper({
    children,
    scale = 1.02,
    tapScale = 0.95,
    y = -4,
    className,
    as = 'div', // 默认为 div
    ...props
}: MotionWrapperProps) {
    const Component = motion(as as any);

    return (
        <Component
            className={className}
            whileHover={{
                scale: scale,
                y: y,
                transition: springs.gentle,
            }}
            whileTap={{
                scale: tapScale,
                transition: springs.stiff,
            }}
            {...props}
        >
            {children}
        </Component>
    );
}
