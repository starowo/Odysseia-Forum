// 自动导入所有 mascot 图片
// 匹配 /src/assets/images/mascot/ 下的所有图片文件
const mascotImagesGlob = import.meta.glob('@/assets/images/mascot/*.{png,jpg,jpeg,webp,gif}', {
    eager: true,
    as: 'url'
});

// 构建映射表: filename (no ext) -> image url
export const MASCOT_IMAGES: Record<string, string> = Object.entries(mascotImagesGlob).reduce((acc, [path, module]) => {
    // 从路径中提取文件名: /src/assets/images/mascot/hi.png -> hi
    const fileName = path.split('/').pop()?.split('.')[0];
    if (fileName) {
        acc[fileName] = module;
    }
    return acc;
}, {} as Record<string, string>);

// 导出类型，虽然现在是 string，但保留类型别名以便后续扩展
export type MascotEmotion = string;

