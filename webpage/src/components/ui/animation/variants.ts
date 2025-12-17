import { Variants } from 'framer-motion';

// 弹簧物理配置
export const springs = {
    stiff: { type: "spring", stiffness: 300, damping: 20 }, // 硬朗，适合小元素
    soft: { type: "spring", stiffness: 100, damping: 20 },  // 柔和，适合大布局
    bouncy: { type: "spring", stiffness: 400, damping: 10 }, // Q弹，适合强调
    gentle: { type: "spring", stiffness: 120, damping: 14 }, // 温和，通用
};

// 通用变体
export const fadeVariants: Variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
};

export const slideUpVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
};

export const scaleVariants: Variants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1 },
};

// 列表容器变体（用于子元素交错动画）
export const staggerContainer: Variants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.05,
            delayChildren: 0.1,
        },
    },
};
