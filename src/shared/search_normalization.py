"""固定词典版本的繁简及港台地区用语搜索规范化。"""

from importlib.metadata import version

from opencc import OpenCC

# 实际安装版本随 uv.lock 固定；词典升级自动隔离缓存和历史回填。
# 修改转换顺序或算法时需递增规则末尾的版本号。
SEARCH_NORMALIZATION_VERSION = f"opencc-{version('opencc')}-s2t-hk2sp-s2t-tw2sp-v1"
SEARCH_CONVERSION_CONFIGS = ("s2t.json", "hk2sp.json", "s2t.json", "tw2sp.json")
_CONVERTERS = tuple(OpenCC(config) for config in SEARCH_CONVERSION_CONFIGS)


def normalize_search_text(text: str) -> str:
    """按固定顺序将搜索副本统一为大陆简体字形和词典收录的地区词。"""
    # 两次统一字形使简体化地区词和混合写法也能命中繁体地区词典。
    for converter in _CONVERTERS:
        text = converter.convert(text)
    return text
