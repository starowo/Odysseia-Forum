import {
  CHANNEL_CATEGORIES,
  type SidebarChannelCategory,
  type SidebarChannelItem,
} from './channelCategories.private';

export interface VirtualTag {
  id: string;
  name: string;
  icon?: string;
}

export interface VirtualTagCategory {
  name: string;
  tags: VirtualTag[];
}

export { CHANNEL_CATEGORIES };
export type { SidebarChannelCategory, SidebarChannelItem };

/**
 * 这里不再把真实论坛频道硬编码成“虚拟 tag”。
 * 真实频道来自私有配置 [`CHANNEL_CATEGORIES`](webpage/src/shared/config/channelCategories.private.ts)，
 * 而 ΙΛΙΑΣ 子服资源仍然作为映射 tag 入口存在。
 */
export const VIRTUAL_TAG_CATEGORIES: VirtualTagCategory[] = [
  {
    name: 'ΙΛΙΑΣ 映射',
    tags: [
      { id: 'ilias-text', name: 'ΙΛΙΑΣ-纯文字' },
      { id: 'ilias-light', name: 'ΙΛΙΑΣ-轻前端' },
      { id: 'ilias-heavy', name: 'ΙΛΙΑΣ-重前端' },
    ],
  },
];

export const ALL_VIRTUAL_TAGS = VIRTUAL_TAG_CATEGORIES.flatMap((cat) => cat.tags);

export const findVirtualTagByName = (name: string) => ALL_VIRTUAL_TAGS.find((tag) => tag.name === name);
