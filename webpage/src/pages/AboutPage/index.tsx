import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Github } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import backgroundImage from '@/assets/images/background/spring.png';
import { APP_VERSION } from '@/shared/config/appInfo';
import { WordLogoStatic } from '@/shared/ui/loaders/WordLogoStatic';

const GITHUB_REPO_URL = 'https://github.com/shiyue137mh-netizen/Odysseia-Forum-Newpage';
const CONTRIBUTORS_URL = `${GITHUB_REPO_URL}/graphs/contributors`;
const CONTRIBUTORS_API_URL =
  'https://api.github.com/repos/shiyue137mh-netizen/Odysseia-Forum-Newpage/contributors?per_page=100';

interface GithubContributor {
  id: number;
  login: string;
  html_url: string;
  avatar_url: string;
  contributions: number;
  type?: string;
}

export function AboutPage() {
  const navigate = useNavigate();
  const hasSpawnedRef = useRef(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const [contributors, setContributors] = useState<GithubContributor[]>([]);
  const [contributorsError, setContributorsError] = useState(false);

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

  useEffect(() => {
    let isActive = true;

    const loadContributors = async () => {
      try {
        const response = await fetch(CONTRIBUTORS_API_URL, {
          headers: {
            Accept: 'application/vnd.github+json',
          },
        });

        if (!response.ok) {
          throw new Error(`GitHub contributors request failed: ${response.status}`);
        }

        const data = (await response.json()) as GithubContributor[];
        if (!isActive) return;
        setContributors(
          data.filter((contributor) => {
            const login = contributor.login.toLowerCase();
            return contributor.type !== 'Bot' && !login.endsWith('[bot]') && !login.includes('bot');
          }),
        );
        setContributorsError(false);
      } catch {
        if (!isActive) return;
        setContributorsError(true);
      }
    };

    void loadContributors();

    return () => {
      isActive = false;
    };
  }, []);

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

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-8 md:px-8">
        <div className="mx-auto w-full max-w-3xl">
          <div className="w-full">
            <div className="rounded-2xl border border-[var(--od-border-strong)]/60 bg-[color-mix(in_oklab,var(--od-bg-secondary)_58%,transparent)] p-6 shadow-2xl backdrop-blur-lg md:p-7">
              <div className="mb-5 flex items-center justify-center md:justify-center">
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
                  href={GITHUB_REPO_URL}
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

              <div className="mt-8 border-t border-[var(--od-border-strong)]/18 pt-7 text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--od-text-label)]">
                  Contributors
                </p>
                <h2 className="mt-3 text-xl font-semibold tracking-tight text-[var(--od-text-primary)]">
                  感谢一起建房子的宝宝们
                </h2>
                <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)]">
                  没有大家一起递砖、补墙、修修小角落，就不会有现在的索引页。这里把每一位帮忙搭房子的宝宝都放出来。
                </p>

                <div className="mt-5 px-1">
                  {contributors.length > 0 ? (
                    <div className="flex flex-wrap justify-center gap-2.5 sm:gap-3">
                      {contributors.map((contributor) => (
                        <a
                          key={contributor.id}
                          href={contributor.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title={`${contributor.login} · ${contributor.contributions} commits`}
                          className="group inline-flex flex-col items-center gap-1.5 text-center"
                        >
                          <img
                            src={`${contributor.avatar_url}&s=96`}
                            alt={contributor.login}
                            className="h-12 w-12 rounded-full border border-[var(--od-border-strong)]/18 object-cover transition-transform duration-200 group-hover:scale-[1.04] sm:h-14 sm:w-14"
                            loading="lazy"
                            decoding="async"
                            referrerPolicy="no-referrer"
                          />
                          <span className="max-w-[4.75rem] truncate text-[10px] text-[var(--od-text-primary)]/88 transition-colors duration-200 group-hover:text-[var(--od-text-primary)] sm:text-[11px]">
                            {contributor.login}
                          </span>
                        </a>
                      ))}
                    </div>
                  ) : contributorsError ? (
                    <a
                      href={CONTRIBUTORS_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center text-sm text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
                    >
                      这会儿没把头像名单拉下来，点我去 GitHub 看完整贡献榜呀。
                    </a>
                  ) : (
                    <div className="flex flex-wrap justify-center gap-2.5 sm:gap-3">
                      {Array.from({ length: 12 }).map((_, index) => (
                        <div key={index} className="flex flex-col items-center gap-1.5">
                          <div className="h-12 w-12 animate-pulse rounded-full bg-[var(--od-bg-tertiary)] sm:h-14 sm:w-14" />
                          <div className="h-2.5 w-12 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-5 text-center">
                    <a
                      href={CONTRIBUTORS_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center text-sm text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
                    >
                      去 GitHub 看完整贡献记录
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
