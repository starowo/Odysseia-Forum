import { motion, useAnimation } from 'framer-motion';
import { LucideIcon, LucideProps } from 'lucide-react';
import { useEffect, useState } from 'react';
import { springs } from './variants';

interface AnimatedIconProps extends Omit<LucideProps, 'ref'> {
    icon: LucideIcon | React.ComponentType<any>;
    animation?: 'scale' | 'rotate' | 'shake' | 'pulse' | 'bounce' | 'spin' | 'flyUp';
    trigger?: 'hover' | 'click' | 'visible' | 'none';
    duration?: number;
    isHovered?: boolean;
    isActive?: boolean;
}

export function AnimatedIcon({
    icon: Icon,
    animation = 'scale',
    trigger = 'hover',
    duration = 0.3,
    className,
    isHovered,
    isActive,
    ...props
}: AnimatedIconProps) {
    const controls = useAnimation();
    const [internalHover, setInternalHover] = useState(false);

    const effectiveHover = isHovered !== undefined ? isHovered : internalHover;

    const variants = {
        scale: {
            initial: { scale: 1 },
            animate: { scale: 1.2 },
        },
        rotate: {
            initial: { rotate: 0 },
            animate: { rotate: 90 },
        },
        spin: {
            initial: { rotate: 0 },
            animate: { rotate: 360 },
        },
        shake: {
            initial: { x: 0 },
            animate: { x: [0, -1.5, 1.5, -1.5, 1.5, 0] },
        },
        pulse: {
            initial: { scale: 1 },
            animate: { scale: [1, 1.1, 1] },
        },
        bounce: {
            initial: { y: 0 },
            animate: { y: [0, -4, 0] },
        },
        flyUp: {
            initial: { y: 0, opacity: 1 },
            animate: { y: [0, -20, 20, 0], opacity: [1, 0, 0, 1] },
        },
    };

    const currentVariant = variants[animation];

    const handleHoverStart = () => {
        if (trigger === 'hover' && isHovered === undefined) {
            setInternalHover(true);
        }
    };

    const handleHoverEnd = () => {
        if (trigger === 'hover' && isHovered === undefined) {
            setInternalHover(false);
        }
    };

    const handleClick = () => {
        if (trigger === 'click') {
            controls.start('animate').then(() => controls.start('initial'));
        }
    };

    useEffect(() => {
        if (trigger === 'visible') {
            controls.start('animate');
        }
    }, [trigger, controls]);

    useEffect(() => {
        if (isHovered !== undefined) {
            if (isHovered) {
                controls.start('animate');
            } else {
                controls.start('initial');
            }
        }
    }, [isHovered, controls]);

    useEffect(() => {
        if (isActive) {
            controls.start('animate').then(() => {
                controls.start('initial');
            });
        }
    }, [isActive, controls]);

    const getAnimateProp = () => {
        if (trigger === 'hover') {
            return effectiveHover ? 'animate' : 'initial';
        }
        if (trigger === 'visible') {
            return 'animate';
        }
        return controls;
    };

    const getTransition = () => {
        if (animation === 'spin') {
            return { duration: 1, ease: "linear", repeat: Infinity };
        }
        if (animation === 'pulse') {
            return { duration: duration, ease: "easeInOut", repeat: effectiveHover ? Infinity : 0, repeatType: "reverse" as const };
        }
        if (animation === 'shake' || animation === 'bounce') {
            return { duration: 0.5, ease: "easeInOut" };
        }
        if (animation === 'flyUp') {
            return { duration: 0.6, times: [0, 0.4, 0.41, 1], ease: "easeInOut" };
        }
        return springs.stiff;
    };

    return (
        <motion.div
            className={`inline-flex items-center justify-center leading-none ${className || ''}`}
            onMouseEnter={handleHoverStart}
            onMouseLeave={handleHoverEnd}
            onClick={handleClick}
            initial="initial"
            animate={getAnimateProp()}
            variants={currentVariant}
            transition={getTransition()}
        >
            <Icon {...props} className="w-full h-full" />
        </motion.div>
    );
}
