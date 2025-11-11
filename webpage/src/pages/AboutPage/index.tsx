import { Github } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import backgroundImage from '@/assets/images/background/winter.png';

export function AboutPage() {
  return (
    <MainLayout showTopBar={false}>
      <div 
        className="fixed inset-0 lg:left-[240px] bg-cover bg-center bg-no-repeat flex items-center justify-center p-8"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      >
        <div className="max-w-2xl w-full">
          {/* 主卡片 - 调整透明度 */}
          <div className="rounded-2xl bg-[#2b2d31]/80 backdrop-blur-lg p-8 border border-[#3f4147]/50 shadow-2xl">
            {/* Logo */}
            <div className="mb-8 flex justify-center">
              <img 
                src={forumIcon} 
                alt="类脑ΟΔΥΣΣΕΙΑ" 
                className="h-24 w-24 rounded-2xl shadow-lg"
              />
            </div>

            {/* 标题 */}
            <h2 className="mb-6 text-center text-3xl font-bold text-[#f2f3f5]">
              类脑ΟΔΥΣΣΕΙΑ
            </h2>

            {/* 核心理念 */}
            <div className="mb-8">
              <p className="text-center text-lg leading-relaxed text-[#e3e5e8]">
                致力于对人工智能知识与技术的无尽探求，
                <br />
                踏上更为辉煌的征程。
                <br />
                <span className="mt-4 block text-[#b5bac1] italic">
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
                className="flex items-center gap-2 rounded-lg bg-[#5865f2] px-6 py-3 text-sm font-medium text-white transition-all duration-200 hover:bg-[#4752c4] hover:scale-105 shadow-lg"
              >
                <Github className="h-5 w-5" />
                <span>访问 GitHub 仓库</span>
              </a>
            </div>

            {/* 版本信息 */}
            <div className="text-center">
              <p className="text-sm text-[#b5bac1]">
                Version 1.0.0 · Powered by Discord
              </p>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
