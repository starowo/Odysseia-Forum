from dataclasses import dataclass


@dataclass(frozen=True)
class TagDTO:
    """
    用于在各层之间传输标签数据
    """

    id: int
    name: str
