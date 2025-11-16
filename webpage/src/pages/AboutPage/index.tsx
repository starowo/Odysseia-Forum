import { useRef } from 'react';
import { Github } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import backgroundImage from '@/assets/images/background/winter.png';

export function AboutPage() {
  const hasSpawnedRef = useRef(false);

  // 点击服务器头像时才加载 oneko.js，小彩蛋
  const handleSpawnNeko = () => {
    // 已经触发过就不再重复注入
    if (hasSpawnedRef.current) return;

    // 如果页面上已经有 oneko 实例，也不再注入脚本
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

  return (
    <MainLayout showTopBar={false}>
      <div
        className="fixed inset-0 lg:left-[240px] bg-cover bg-center bg-no-repeat flex items-center justify-center p-8"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      >
        <div className="max-w-2xl w-full">
          {/* 主卡片 - 调整透明度 */}
          <div className="rounded-2xl bg-[color-mix(in_oklab,var(--od-bg-secondary)_85%,transparent)] backdrop-blur-lg p-8 border border-[var(--od-border-strong)]/60 shadow-2xl">
            {/* Logo - 点击触发 oneko 小猫彩蛋 */}
            <div
              className="mb-8 flex justify-center cursor-pointer select-none"
              onClick={handleSpawnNeko}
              title="试着点点我？"
            >
              <img
                src={forumIcon}
                alt="类脑ΟΔΥΣΣΕΙΑ"
                className="h-24 w-24 rounded-2xl shadow-lg"
              />
            </div>

            {/* 标题 */}
            <h2 className="mb-6 text-center text-3xl font-bold text-[var(--od-text-primary)]">
              类脑ΟΔΥΣΣΕΙΑ
            </h2>

            {/* 核心理念 */}
            <div className="mb-8">
              <p className="text-center text-lg leading-relaxed text-[var(--od-text-primary)]">
                致力于对人工智能知识与技术的无尽探求，
                <br />
                踏上更为辉煌的征程。
                <br />
                <span className="mt-4 block text-[var(--od-text-secondary)] italic">
                  玄想阑珊处，奇点自相生。
                </span>
              </p>
            </div>

            {/* GitHub链接 */}
            <div className="mb-6 flex justify-center">
              <a
                href="https://github.com/starowo/Odysseia-Forum"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-6 py-3 text-sm font-medium text-white transition-all duration-200 hover:bg-[var(--od-accent-hover)] hover:scale-105 shadow-lg"
              >
                <Github className="h-5 w-5" />
                <span>访问 GitHub 仓库</span>
              </a>
            </div>

            {/* 版本信息 */}
            <div className="text-center">
              <p className="text-sm text-[var(--od-text-secondary)]">
                Version 1.0.0 · Powered by Discord
              </p>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
