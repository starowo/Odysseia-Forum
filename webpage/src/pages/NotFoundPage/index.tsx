import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMascotStore } from '@/features/mascot/store/mascotStore';

export function NotFoundPage() {
    const navigate = useNavigate();
    const { reactToError } = useMascotStore();

    useEffect(() => {
        // Trigger mascot reaction on mount
        reactToError('notFound');
    }, [reactToError]);

    return (
        <div className="flex min-h-[80vh] flex-col items-center justify-center p-4 text-center">
            <h1 className="mb-4 text-8xl font-bold text-[var(--od-text-primary)] opacity-20">404</h1>
            <h2 className="mb-6 text-2xl font-semibold text-[var(--od-text-primary)]">
                页面走丢了...
            </h2>
            <p className="mb-8 max-w-md text-[var(--od-text-secondary)]">
                看来你来到了一个未知的领域。不过别担心，看板娘会陪着你的。
            </p>
            <button
                onClick={() => navigate('/')}
                className="rounded-full bg-[var(--od-primary)] px-8 py-3 font-medium text-white transition-transform hover:scale-105 active:scale-95"
            >
                返回首页
            </button>
        </div>
    );
}
