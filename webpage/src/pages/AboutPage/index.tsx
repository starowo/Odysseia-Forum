import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Github } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import backgroundImage from '@/assets/images/background/spring.png';
import { APP_VERSION } from '@/shared/config/appInfo';
import { WordLogoStatic } from '@/shared/ui/loaders/WordLogoStatic';

export function AboutPage() {
  const navigate = useNavigate();
  const hasSpawnedRef = useRef(false);
  const [isLeaving, setIsLeaving] = useState(false);

  const handleSpawnNeko = () => {
    if (hasSpawnedRef.current) return;

    if (document.getElementById('oneko')) {
      hasSpawnedRef.current = true;
      return;
    }

    const script = document.createElement('script');
    script.src = '/oneko/oneko.js';
    script.async = true;
    script.dataset.cat = '/oneko/oneko.gif';
    document.body.appendChild(script);
    hasSpawnedRef.current = true;
  };

  useEffect(() => {
    if (!isLeaving) return;

    const timeoutId = window.setTimeout(() => {
      if (window.history.length > 1) {
        navigate(-1);
        return;
      }

      navigate('/', { replace: true });
    }, 180);

    return () => window.clearTimeout(timeoutId);
  }, [isLeaving, navigate]);

  return (
    <motion.div
      className="relative min-h-screen overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: isLeaving ? 0 : 1 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
    >
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      />
      <div className="absolute inset-0 bg-black/14" />

      <div className="relative z-10 flex min-h-screen items-center px-4 py-8 md:px-8">
        <div className="mx-auto w-full max-w-7xl md:pl-[8%] lg:pl-[10%]">
          <div className="w-full max-w-lg">
            <div className="rounded-2xl border border-[var(--od-border-strong)]/60 bg-[color-mix(in_oklab,var(--od-bg-secondary)_58%,transparent)] p-6 shadow-2xl backdrop-blur-lg md:p-7">
              <div className="mb-5 flex items-center justify-start">
                <button
                  type="button"
                  onClick={() => setIsLeaving(true)}
                  disabled={isLeaving}
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--od-border)] bg-[color-mix(in_oklab,var(--od-bg)_68%,transparent)] px-4 py-2 text-sm font-medium text-[var(--od-text-primary)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--od-accent)]/45 hover:text-[var(--od-accent)] disabled:cursor-not-allowed disabled:opacity-55"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>返回</span>
                </button>
              </div>

              <div
                className="mb-7 flex cursor-pointer select-none justify-center"
                onClick={handleSpawnNeko}
                title="试着点点我？"
              >
                <img
                  src={forumIcon}
                  alt="类脑ΟΔΥΣΣΕΙΑ"
                  className="h-20 w-20 rounded-2xl shadow-lg md:h-24 md:w-24"
                />
              </div>

              <div className="mb-5 flex flex-col items-center justify-center gap-2">
                <span className="text-2xl font-bold tracking-[0.2em] text-[var(--od-text-primary)]">类脑</span>
                <WordLogoStatic className="h-[1.125rem] text-[var(--od-text-primary)]" />
              </div>

              <div className="mb-6">
                <p className="text-center text-base leading-relaxed text-[var(--od-text-primary)] md:text-lg">
                  致力于对人工智能知识与技术的无尽探求，
                  <br />
                  踏上更为辉煌的征程。
                  <br />
                  <span className="mt-4 block italic text-[var(--od-text-secondary)]">
                    玄想阑珊处，奇点自相生。
                  </span>
                </p>
              </div>

              <div className="mb-5 flex justify-center">
                <a
                  href="https://github.com/starowo/Odysseia-Forum"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-6 py-3 text-sm font-medium text-white shadow-lg transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
                >
                  <Github className="h-5 w-5" />
                  <span>访问 GitHub 仓库</span>
                </a>
              </div>

              <div className="text-center">
                <p className="text-sm text-[var(--od-text-secondary)]">
                  前端版本 {APP_VERSION} · Odysseia Forum Webpage
                </p>
                <p className="mt-1 text-xs text-[var(--od-text-tertiary)]">最近更新：banner申请功能</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
