import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import { CHANNEL_CATEGORIES } from '@/shared/config/channelCategories.private';

export interface ApiChannel {
  guild_id: string;
  channel_id: string;
  name: string;
  available_tags: { tag_id: number; name: string }[];
  virtual_tags: { tag_name: string; source_channel_ids: string[] }[];
  mapped_source_channels?: { channel_id: string; channel_name: string; available_tags: { tag_id: number; name: string }[] }[];
  real_thread_count: number;
  virtual_thread_count: number;
  total_thread_count: number;
}

export interface UnifiedChannel {
  id: string;
  name: string;
  groupId?: string;
  groupName?: string;
}

export function useChannels() {
  return useQuery({
    queryKey: ['meta', 'channels'],
    queryFn: async () => {
      try {
        const response = await apiClient.get<ApiChannel[]>('/meta/channels');
        const apiChannels = response.data;
        
        // 我们需要把后端的平铺频道，和前端静态配置的"分组(Category)"映射起来
        // 如果后端频道在静态配置中找不到分组，我们就给个默认的"其他区"分组
        const channels: UnifiedChannel[] = [];
        
        // 建立静态映射加速查找
        const dynamicMap = new Map<string, { groupId: string; groupName: string }>();
        CHANNEL_CATEGORIES.forEach((category, catIndex) => {
          category.channels.forEach((c) => {
            dynamicMap.set(c.id, { 
              groupId: `cat-${catIndex}`, 
              groupName: category.name 
            });
          });
        });

        // 收集所有被主频道映射的子服务器源频道 ID
        // 这些源频道不应该被独立展示在侧边栏中
        const hiddenSourceChannels = new Set<string>();
        for (const ac of apiChannels) {
          if (ac.mapped_source_channels) {
            for (const mapSrc of ac.mapped_source_channels) {
              hiddenSourceChannels.add(mapSrc.channel_id);
            }
          }
        }

        const seen = new Set<string>();
        for (const ac of apiChannels) {
          // 避免重复渲染
          if (seen.has(ac.channel_id)) continue;
          
          // 如果该频道已经被映射到其他主频道下面（作为虚拟标签的来源），就不要在左侧展示了
          if (hiddenSourceChannels.has(ac.channel_id)) continue;

          seen.add(ac.channel_id);

          const cat = dynamicMap.get(ac.channel_id);
          // 在静态表里没有配置的主频道，展示进"其他区"
          channels.push({
            id: ac.channel_id,
            name: ac.name,
            groupId: cat?.groupId || 'cat-other',
            groupName: cat?.groupName || '其他区',
          });
        }
        
        return {
          source: 'api' as const,
          channels,
          apiData: apiChannels,
        };
      } catch (err) {
        console.warn('Failed to fetch /meta/channels, falling back to static config', err);
        // Fallback 到静态配置
        const fallbackChannels: UnifiedChannel[] = [];
        CHANNEL_CATEGORIES.forEach((category, catIndex) => {
          category.channels.forEach((c) => {
            fallbackChannels.push({
              id: c.id,
              name: c.name,
              groupId: `cat-${catIndex}`,
              groupName: category.name,
            });
          });
        });
        
        return {
          source: 'static' as const,
          channels: fallbackChannels,
          apiData: null,
        };
      }
    },
    staleTime: 10 * 60 * 1000, // 10 minutes, 频道数据不常变
    retry: 1, // 失败重试1次后降级
  });
}
