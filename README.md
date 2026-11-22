<<<<<<< HEAD
# 🎹 music_library

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.ja)

**Pythonで作られた、微分音も出せるシンセサイザーです。**

1オクターブを好きな数に等分した音律(N-EDO)で作曲・演奏でき、純正律の座標指定や、定義和音(機能式)による和音の記述にも対応しています。付属の曲(キラキラ星、カノン、微分音コード進行ギャラリーなど)をすぐ再生でき、WAVファイルに書き出すこともできます。

---

## ✨ 特長

- 🎵 **任意のN-EDOに対応**: 12平均律はもちろん、24・31・41など好きな等分数で演奏できる
- ➕ **微分音の記法**: `C+4`(1ステップ上げる)、`C-4`(1ステップ下げる)のように音名へ直接書ける
- 🧮 **純正律の座標指定**: 素数の指数で音程を指定し、最も近いN-EDOの音に量子化して鳴らす
- 🎼 **定義和音(機能式)**: `"O"`, `"<,"`, `"O𐑣,"` のような式で和音を書ける
- 🌊 **12種類の波形**: サイン波、矩形波(デューティ比5種)、ノコギリ波、三角波、ノイズなど
- 🎚️ **ADSRエンベロープ**: attack / decay / sustain / release を調整できる
- 🎛️ **マルチトラック**: 複数パートを重ねて再生、ソロ再生も可能
- 💾 **WAV書き出し**: 作った曲をそのまま保存できる

## 📦 必要なもの

- Python 3.10 以上
- [NumPy](https://numpy.org/) / [SciPy](https://scipy.org/) / [sounddevice](https://python-sounddevice.readthedocs.io/)

```bash
pip install numpy scipy sounddevice
```

> 🐧 Linuxでは、sounddeviceの動作にPortAudioが必要です(例: `sudo apt install libportaudio2`)。

## 🚀 はじめかた

```bash
git clone https://github.com/hiroshima424jpsb-star/music_library.git
cd music_library
```

リポジトリのルートで Python を起動し、付属の曲を再生してみましょう。

```python
import music

music.music(0)   # キラキラ星を再生
```

### 付属の曲

| index | 曲名 | 推奨の音律 |
| ----- | ---- | ---------- |
| 0 | キラキラ星 | 12-EDO |
| 1 | あめあめふれふれ | 12-EDO |
| 2 | ねこふんじゃった | 12-EDO |
| 3 | 聖者の行進 | 12-EDO |
| 4 | オーラリー | 12-EDO |
| 5 | カノン | 12-EDO |
| 6 | どんぐりころころ | 12-EDO |
| 7 | カエルの歌 | 12-EDO |
| 8 | 微分音コード進行ギャラリー | **41-EDO** |

```python
import music

music.get_music_titles()           # 曲名の一覧
music.get_music_dict()             # {曲名: index}

music.music(8)                     # 推奨の音律(41-EDO)で自動的に再生
music.music(5, solo=1)             # カノンの2番目のトラックだけ再生

m = music.music(5, is_play=False)  # 再生せずに生成だけ行う
m.save("canon.wav")                # WAVファイルに保存
```

## 🎼 自分で曲を作る

```python
from music import Ongaku

m = Ongaku(equal=24)               # 24-EDO(四分音を含む)

m.tone("C4", long=4)               # 4分音符のド
m.tone("C+4")                      # 1ステップ上(24-EDOでは四分音)
m.tone("E4")
m.rest()                           # 休符
m.tone(("C4", "E4", "G4"), long=1) # 和音(全音符)

m.play()                           # 再生
m.save("my_song.wav")              # 保存
```

### 音の書き方

`音名(C〜B) + 臨時記号 + オクターブ(数字1桁)` で指定します。基準は `A4 = 440Hz` です。

| 記号 | 意味 |
| ---- | ---- |
| `#` / `b` | 半音上げる / 下げる(その音律での「半音」にあたるステップ数) |
| `+` / `-` | **1ステップ**上げる / 下げる(微分音) |

### 主な引数・設定

| 項目 | 説明 |
| ---- | ---- |
| `long` | 音の長さ(4=4分音符、8=8分音符 …) |
| `dot` | 付点 |
| `staccato` | スタッカート |
| `presses` | 同じ音を繰り返す回数 |
| `rhythm` | `"2/3"` のような比率での長さ調整 |
| `m.bpm` | テンポ(初期値 120) |
| `m.set_key("D")` / `m.transpose("D")` | 調の設定 / 転調 |
| `m.next_edit()` | 次のトラックの編集に移る |
| `m.change_equal(31)` | 音律の変更 |
| `m.main_volume` / `m.volume` | 全体 / 現在のトラックの音量 |

### 波形

```python
m.change_wave_type("square-25")
```

`sin` / `square-12.5` / `square-25` / `square-50` / `square-75` / `square-87.5` / `sawtooth` / `triangle` / `pet` / `digital_piano` / `brown_noise` / `pink_noise`

### エンベロープ

```python
m.envelope_data.update({"attack": 0.01, "decay": 0.2, "sustain": 0.6, "release": 0.05})
```

`sustain` は1以下、`attack + decay + release` は1秒未満にする必要があります。

### 純正律の座標指定

素数の指数(`2, 3/2, 5/4, 7/4, 11/4, 13/4` の順)で音程を指定すると、最も近いN-EDOの音に量子化して鳴らします。

```python
m = Ongaku(equal=41)
m.ji_tone(((0, 0), (1, 0), (0, 1)), long=1)   # 純正律の長三和音
```

### 定義和音(機能式)

`func_tone` に機能式を渡すと和音を鳴らせます。初期設定では `"O"` が純正律の長三和音になり、`"<"` で左、`">"` で右へ根音が移ります。`,` や `'` で追加音を重ねられます。

```python
m = Ongaku(equal=41)
m.func_tone("O", long=2)         # 主和音
m.func_tone("<,", long=2)        # 左に移った和音 + 追加音
m.func_tone(("O,", "/O"), long=1) # 和音 + ベース(/)
```

機能式の記法の詳細は、元となっている _pasmacafcól_ の[解説動画](https://www.youtube.com/watch?v=pYSICBXBxpo)と[公式の解説ページ](https://lamplight0.sakura.ne.jp/a/langs/saf_sdic_iframe_wordpage.php?ic=E8tw5)を参照してください。

## 📁 ディレクトリ構成

```
music_library/
├── music/
│   ├── __init__.py     # 公開API(music, get_music_titles, get_music_dict, Ongaku, DefChord)
│   ├── core.py         # シンセサイザー本体(Ongaku / Calculator / DefChord)
│   └── music_data.py   # 付属の曲データ
├── .gitignore
└── README.md
```

## 🙏 クレジット

このリポジトリには、次の作品に基づく部分が含まれています。

- **定義和音 (`DefChord`)**: [_pasmacafcól_](https://lamplight0.sakura.ne.jp/a/langs/saf_sdic_iframe_wordpage.php?ic=E8tw5) の再現実装です。原作は [LΛMPLIGHT](https://www.youtube.com/@L4MPLIGHT/) 氏によるもの([解説動画](https://www.youtube.com/watch?v=pYSICBXBxpo))。Copyright (c) 2026 zibluko。CC BY-NC-SA 4.0 で提供されています。
- **微分音コード進行ギャラリー** (`music8`): [LΛMPLIGHT](https://www.youtube.com/@L4MPLIGHT/) 氏の[動画](https://www.youtube.com/watch?v=ci_LQmq9dNc)に基づいています。CC BY-NC-SA 4.0 で提供されています。

## 📜 ライセンス

<a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.ja"><img alt="クリエイティブ・コモンズ・ライセンス" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a>

本作品は
[クリエイティブ・コモンズ 表示 - 非営利 - 継承 4.0 国際 ライセンス (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.ja)
の下に提供されています。

- **表示 (BY)**: 作者のクレジットを表示し、ライセンスへのリンクを示し、変更した場合はその旨を明記してください。
- **非営利 (NC)**: 営利目的で利用してはいけません。
- **継承 (SA)**: 改変した場合は、元の作品と同じ CC BY-NC-SA 4.0 ライセンスで公開してください。

ライセンスの全文: <https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.ja>
=======
Pythonで作られた微分音も出せるシンセサイザーです。
>>>>>>> 9482cc7432b3b1d88fa0143b97013c3365ad6faa
