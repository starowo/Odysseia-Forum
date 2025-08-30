from enum import Enum

class DefaultPreferences(Enum):
    # 预览图显示模式
    PREVIEW_IMAGE_MODE = "thumbnail" # "thumbnail" 或 "image"

    # 默认豁免词
    EXEMPTION_MARKERS = ["禁", "🈲"]

    # 每页结果数量
    RESULTS_PER_PAGE = 5