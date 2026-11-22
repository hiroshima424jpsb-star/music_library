"""音楽を作るモジュール"""

from .core import Ongaku, DefChord
from . import music_data


def music(index: int = 0, m: Ongaku | None = None, solo: int | None = None, is_play: bool = True) -> Ongaku:
    """指定された曲を実行"""
    if 0 <= index < len(music_data.music_titles):
        music = m or Ongaku(equal=music_data.music_recommended_edoes[index])
        getattr(music_data, f"music{index}")(m=music)
        if is_play:
            music.play(solo=solo)
        return music
    else:
        raise IndexError(f"index {index} is out of range")


def get_music_titles(index: None | int = None) -> tuple[str, ...] | str:
    """音楽のタイトルを返す"""
    if index is None:
        return music_data.music_titles
    else:
        return music_data.music_titles[index]


def get_music_dict() -> dict[str, int]:
    """音楽の辞書を返す {title: index}"""
    return dict(zip(music_data.music_titles, range(len(music_data.music_titles))))


__all__ = ["music", "get_music_titles", "get_music_dict", "Ongaku", "DefChord"]
