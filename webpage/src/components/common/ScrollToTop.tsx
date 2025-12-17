import { useState, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';
import { AnimatedIcon } from '@/components/ui/animation/AnimatedIcon';

export function ScrollToTop() {
  const [isVisible, setIsVisible] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    const toggleVisibility = () => {
      // 滚动超过 300px 时显示按钮
      if (window.pageYOffset > 300) {
        setIsVisible(true);
      } else {
        setIsVisible(false);
      }
    };

    window.addEventListener('scroll', toggleVisibility);
    return () => window.removeEventListener('scroll', toggleVisibility);
  }, []);

  const scrollToTop = () => {
    setIsAnimating(true);
    setTimeout(() => setIsAnimating(false), 600);
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  };

  return (
    <button
      onClick={scrollToTop}
      className={`fixed bottom-20 right-4 z-50 flex items-center justify-center leading-none rounded-full bg-[var(--od-accent)] p-3 text-white shadow-lg transition-all duration-300 hover:scale-110 hover:bg-[var(--od-accent-hover)] hover:shadow-xl lg:bottom-8 ${isVisible
        ? 'pointer-events-auto opacity-100 translate-y-0'
        : 'pointer-events-none opacity-0 translate-y-4'
        }`}
      aria-label="回到顶部"
      title="回到顶部"
    >
      <AnimatedIcon
        icon={ArrowUp}
        className="h-6 w-6"
        animation={isAnimating ? 'flyUp' : 'bounce'}
        trigger={isAnimating ? 'none' : 'hover'}
        isActive={isAnimating}
      />
    </button>
  );
}
