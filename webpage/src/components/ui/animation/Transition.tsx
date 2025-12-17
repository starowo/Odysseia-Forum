import { motion, AnimatePresence, HTMLMotionProps } from 'framer-motion';
import { fadeVariants, slideUpVariants, scaleVariants, springs } from './variants';

interface TransitionProps extends HTMLMotionProps<"div"> {
    children: React.ReactNode;
    type?: 'fade' | 'slide' | 'scale';
    delay?: number;
    className?: string;
    show?: boolean; // 控制 AnimatePresence
}

export function Transition({
    children,
    type = 'fade',
    delay = 0,
    className,
    show = true,
    ...props
}: TransitionProps) {
    const variants = {
        fade: fadeVariants,
        slide: slideUpVariants,
        scale: scaleVariants,
    };

    return (
        <AnimatePresence mode="wait">
            {show && (
                <motion.div
                    className={className}
                    initial="hidden"
                    animate="visible"
                    exit="hidden"
                    variants={variants[type]}
                    transition={{
                        ...springs.soft,
                        delay: delay,
                    }}
                    {...props}
                >
                    {children}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
