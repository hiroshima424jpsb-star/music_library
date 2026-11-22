"""中核部分"""

# ! pip install sounddevice
import re
import math
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from scipy.interpolate import interp1d


class EnvelopeData:
    """エンベロープのデータを管理するクラス"""

    def __init__(self, envelope_data: dict):
        self.envelope_data = envelope_data

    def __setitem__(self, key: str, value: float) -> None:
        temp_data = self.envelope_data.copy()
        temp_data[key] = value
        if temp_data["sustain"] > 1:
            raise ValueError(f"{value} is greater than 1.")
        second = sum([temp_data[k] for k in ["attack", "decay", "release"]])
        if second >= 1:
            raise ValueError(
                f"The sum({second}) of attack, decay and release is greater than 1 second."
            )
        self.envelope_data = temp_data

    def __getitem__(self, key: str) -> float:
        return self.envelope_data[key]

    def update(self, envelope_data: dict) -> None:
        for key, value in envelope_data.items():
            self[key] = value


class Ongaku:
    """音楽を作るクラス"""

    WAVE_TYPES: dict = {
        "sin": lambda t, hz: np.sin(2 * np.pi * hz * t),
        "square-50": lambda t, hz: np.sign(np.sin(2 * np.pi * hz * t)),
        "square-25": lambda t, hz: np.sign(np.sin(2 * np.pi * hz * t) - 1 / np.sqrt(2)),
        "square-12.5": lambda t, hz: np.sign(
            np.sin(2 * np.pi * hz * t) + np.cos(np.pi / 8)
        ),
        "square-75": lambda t, hz: np.sign(np.sin(2 * np.pi * hz * t) + 1 / np.sqrt(2)),
        "square-87.5": lambda t, hz: np.sign(
            np.sin(2 * np.pi * hz * t) - np.cos(np.pi / 8)
        ),
        "sawtooth": lambda t, hz: np.mod(t * hz, 1) * 2 - 1,
        "triangle": lambda t, hz: np.abs(np.mod(2 * t * hz - 0.5, 2) - 1) * 2 - 1,
        "pet": lambda t, hz: np.sum(
            [np.sin(2 * np.pi * hz * t * i) for i in range(1, 10)], axis=0
        ),
        "digital_piano": lambda t, hz: np.sin(2 * np.pi * hz * t + np.sin(2 * np.pi * hz * t * 14) / 2),
        "brown_noise": lambda t, _hz: np.cumsum(np.random.randn(len(t))),
        "pink_noise": lambda t, _hz: Calculator.pink_noise(t),
    }

    def __init__(self, equal: int = 12, a: int = 440, samplerate: int = 44100) -> None:
        self.all_reset()
        self.samplerate = samplerate
        self.calc = Calculator(equal=equal, a=a)
        self.def_chord = DefChord(1, 2, (1, 0), (0, 1))
        self.envelope_data = EnvelopeData(
            {
                "attack": 0.005,
                "decay": 0.3,
                "sustain": 0.8,
                "release": 0.02,
            }
        )

    def all_reset(self) -> None:
        """全てリセット"""
        self.full_song_reset()
        self.change_wave_type("sin")
        self.key: int = 0
        self.bpm: float = 120
        self.long: int = 4
        self.main_volume = 0.7
        self.volume = 1
        self.staccato_ratio = 0.3

    def ji_tone(
        self,
        coordinates: tuple[tuple[int, ...], ...],
        long: int | None = None,
        dot: bool = False,
        staccato: bool = False,
        presses: int = 1,
        rhythm: str = "1/1",
    ) -> None:
        self.tone(
            self.calc.jis_to_tones(coordinates),
            long=long,
            dot=dot,
            staccato=staccato,
            presses=presses,
            rhythm=rhythm,
        )

    def func_tone(
        self,
        funcs: tuple[str, ...] | str,
        octave: int = 0,
        voicing: tuple[int, ...] | None = None,
        adds: tuple[tuple[int, ...], ...] | None = None,
        long: int | None = None,
        dot: bool = False,
        staccato: bool = False,
        presses: int = 1,
        rhythm: str = "1/1",
    ) -> None:
        self.def_chord.voicing_index = 0
        self.ji_tone(
            tuple(
                sum(
                    [
                        self.def_chord.get_ji_from_func(func, octave, voicing)
                        for func in (funcs if isinstance(funcs, tuple) else (funcs,))
                    ],
                    (),
                )
            )
            + (adds if adds else ()),
            long=long,
            dot=dot,
            staccato=staccato,
            presses=presses,
            rhythm=rhythm,
        )

    def change_wave_type(self, wave_type: str) -> None:
        """波形を変更"""
        if wave_type in self.WAVE_TYPES:
            self.func = self.WAVE_TYPES[wave_type]
        else:
            raise ValueError(f"invalid wave type: {wave_type}")

    def change_equal(self, equal: int) -> None:
        """平均律を変更"""
        self.calc.change_equal(equal)

    def full_song_reset(self) -> None:
        """曲のリセット"""
        self.full_songs = [np.array([])]
        self.editing = 0

    def set_key(self, key: str) -> None:
        """調を設定"""
        self.key = self.calc.code[key[0]] + self.calc.accidental(key[1:])

    def transpose(self, transpose: str, is_up: bool = True) -> None:
        """転調"""
        self.key += (1 if is_up else -1) * (
            self.calc.code[transpose[0]] + self.calc.accidental(transpose[1:])
        )

    def tone(
        self,
        tone: str | tuple[str, ...],
        long: int | None = None,
        dot: bool = False,
        staccato: bool = False,
        presses: int = 1,
        rhythm: str = "1/1",
    ) -> None:
        """
        ## 指定の音を鳴らす
        ### 必須引数
        - tone: 音階(大文字) + (臨時記号(#/b)) + オクターブ(数字)
        """
        tones = tone if isinstance(tone, tuple) else (tone,)
        if long is not None:
            self.long = long
        hzs = self.calc.pitch(tones, self.key)
        play_s, gap_s = self.calc.long(self.bpm, self.long, dot, staccato, rhythm)
        # 時間軸の生成
        t = np.linspace(0, play_s, int(self.samplerate * play_s), endpoint=False)
        wave = (
            self.calc.make_wave(play_s, hzs, t, self.func, self.envelope_data)
            * self.volume
        )
        gap = np.zeros(int(self.samplerate * gap_s))
        wave_all = np.concatenate((wave, gap))
        wave_all = np.tile(wave_all, presses)
        self.full_songs[self.editing] = np.concatenate(
            (self.full_songs[self.editing], wave_all)
        )

    def rest(
        self, long: int | None = None, dot: bool = False, rhythm: str = "1/1"
    ) -> None:
        """休符"""
        if long is not None:
            self.long = long
        gap_s = sum(self.calc.long(self.bpm, self.long, dot, False, rhythm))
        gap = np.zeros(int(self.samplerate * gap_s))
        self.full_songs[self.editing] = np.concatenate(
            (self.full_songs[self.editing], gap)
        )

    def play(self, solo: int | None = None) -> None:
        """再生"""
        full_song = self.full_songs if solo is None else [self.full_songs[solo]]
        full_song = self.calc.flexible_sum(full_song) * self.main_volume
        sd.play(full_song, self.samplerate)
        sd.wait()

    def next_edit(self) -> None:
        """次のトラックの編集"""
        self.full_songs += [np.array([])]
        self.editing += 1

    def save(self, path: str | None = None) -> None:
        """保存"""
        default_path = "music.wav"
        path = path or default_path
        full_song = self.calc.flexible_sum(self.full_songs) * self.main_volume
        write(
            path,
            self.samplerate,
            (np.clip(full_song, -1.0, 1.0) * 32767).astype(np.int16),
        )


class Calculator:
    """計算するクラス"""

    def __init__(self, equal: int = 12, a: int = 440):
        self.primes = [2, 3 / 2, 5 / 4, 7 / 4, 11 / 4, 13 / 4]
        self.change_equal(equal)
        self.a = a

    def pitch(self, tones: tuple[str, ...], key: int) -> tuple[float, ...]:
        """音の周波数を返す"""
        hzs = []
        for tone in tones:
            note_name = tone[0]
            octave = int(tone[-1])
            accidental = tone[1:-1]
            if self.code.get(note_name, None) is None:
                raise ValueError(f"The note name is wrong: {note_name}")
            half = self.accidental(accidental)
            # 4オクターブとCからAまでの距離下げる
            point = self.code[note_name] + half + self.equal * (octave - 4) + key
            hzs.append(self.a * 2 ** (point / self.equal) / 2 ** (3 / 4))
        return tuple(hzs)

    def long(
        self, bpm: float, long: int, dot: bool, staccato: bool, rhythm: str
    ) -> tuple[float, float]:
        """音の長さを返す。返り値は(play_s, gap_s)"""
        dot_long = 1.5 if dot else 1
        rhythms = tuple(map(int, rhythm.split("/")))
        # 一小節がlong=1とするとき long が4の時と、bpm が60のときに1になるように 4 * 60 = 240 を掛ける
        total_s = rhythms[0] / rhythms[1] * dot_long * 240 / bpm / long
        play_ratio = 0.3 if staccato else 1
        play_s = total_s * play_ratio
        gap_s = total_s - play_s
        return play_s, gap_s

    def make_wave(
        self,
        play_s: float,
        hzs: tuple[float, ...],
        t: np.ndarray,
        wav_func,
        envelope_data: EnvelopeData,
    ) -> np.ndarray:
        """波を生成する"""
        wave = np.sum([self.norm(wav_func(t, hz)) for hz in hzs], axis=0)
        wave *= self.envelope(envelope_data, t, play_s)
        return wave

    def envelope(
        self, envelope_data: EnvelopeData, t: np.ndarray, play_s: float
    ) -> np.ndarray:
        """エンベロープの波を作る"""
        points = np.array(
            [
                [0.0, 0.0],
                [envelope_data["attack"], 1.0],
                [
                    envelope_data["attack"] + envelope_data["decay"],
                    envelope_data["sustain"],
                ],
                [play_s - envelope_data["release"], envelope_data["sustain"]],
                [play_s, 0.0],
            ]
        )
        x_points = points[:, 0]
        y_points = points[:, 1]
        f_envelope = interp1d(
            x_points,
            y_points,
            kind="linear",
            bounds_error=False,
            fill_value=0.0,
        )
        return f_envelope(t)[0 : len(t)]

    def accidental(self, accidental: str) -> int:
        """臨時記号から半音の数を返す"""
        half = 0
        half += self.half_step * accidental.count("#")
        half -= self.half_step * accidental.count("b")
        half += accidental.count("+")
        half -= accidental.count("-")
        return half

    def flexible_add(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """違う長さの波を足す"""
        if len(a) < len(b):
            a, b = b, a

        res = a.copy()
        res[: len(b)] += b
        return res

    def flexible_sum(self, a: list[np.ndarray]) -> np.ndarray:
        """波を全て足す"""
        res = np.array([])
        for i in a:
            res = self.flexible_add(res, i)
        return self.norm(res)

    def norm(self, a: np.ndarray) -> np.ndarray:
        """正規化"""
        if a.size == 0:
            raise ValueError("music is empty")
        max_val = np.max(np.abs(a))
        if max_val == 0:
            return a
        return a / max_val

    def ji_quantize(self, coordinate: tuple[int, ...]) -> int:
        """座標からステップ数を返す"""
        double = 1
        for dimension, prime in zip(coordinate, self.primes[: len(coordinate)]):
            double *= prime**dimension
        return round(self.equal * math.log2(double))

    def step_to_code(self, step: int) -> str:
        """ステップ数から音階を返す"""
        octave = step // self.equal
        step_octave_less = step % self.equal
        code_name = "C"
        code = 0
        for key, value in list(self.code.items())[:7]:
            if step_octave_less >= value:
                code = value
                code_name = key
        difference = step_octave_less - code
        sharp = difference // self.half_step
        plus = difference % self.half_step
        return f"{code_name}{'#' * sharp}{'+' * plus}{4 + octave}"

    def ji_to_code(self, coordinate: tuple[int, ...]) -> str:
        return self.step_to_code(self.ji_quantize(coordinate))

    def jis_to_tones(self, coordinates: tuple[tuple[int, ...], ...]) -> tuple[str, ...]:
        return tuple([self.ji_to_code(coordinate) for coordinate in coordinates])

    def change_equal(self, equal: int) -> None:
        """平均律を変更"""
        self.equal = equal
        self.code = {
            "C": 0,
            "D": self.ji_quantize((-1, 2)),
            "E": self.ji_quantize((-2, 4)),
            "F": self.ji_quantize((1, -1)),
            "G": self.ji_quantize((0, 1)),
            "A": self.ji_quantize((-1, 3)),
            "B": self.ji_quantize((-2, 5)),
        }
        self.half_step = self.equal - self.code["B"]

    @staticmethod
    def pink_noise(t: np.ndarray) -> np.ndarray:
        """ピンクノイズ"""
        white_noise = np.random.randn(len(t))
        fft_data = np.fft.rfft(white_noise)
        frequencies = np.fft.rfftfreq(len(t))
        frequencies[0] = 0.0
        amplitude_filter = 1 / np.sqrt(frequencies)
        fft_filtered = fft_data * amplitude_filter
        pink_noise = np.fft.irfft(fft_filtered, n=len(t))
        return pink_noise


class DefChord:
    """
    ## 定義和音
    - Reproduced implementation of [_pasmacafcól_][about function formula].
    - Original _pasmacafcól_ created by [LΛMPLIGHT][youtube]([2025][explanatory video]).
    - Copyright (c) 2026 zibluko
    - This work is licensed under [CC BY-NC-SA 4.0][CC].

    [youtube]: https://www.youtube.com/@L4MPLIGHT/
    [about function formula]: https://lamplight0.sakura.ne.jp/a/langs/saf_sdic_iframe_wordpage.php?ic=E8tw5
    [explanatory video]: https://www.youtube.com/watch?v=pYSICBXBxpo
    [CC]: https://creativecommons.org/licenses/by-nc-sa/4.0/
    """

    def __init__(
        self,
        host_axis_index: int,
        guest_axis_index: int,
        host_note: tuple[int, int],
        guest_note: tuple[int, int],
    ):
        self.host_axis_index = host_axis_index
        self.guest_axis_index = guest_axis_index
        self.root = (0, 0)
        self.host_note = host_note
        self.guest_note = guest_note
        self.voicing_index = 0

    def get_add_from_sides(self, left: str, right: str) -> tuple[tuple[int, int], ...]:
        """
        ## 追加音
        - 司次元: ,
        - ,を飛ばす: .
        - 客音から司次元に: '
        - 'を飛ばす: ¯ U+00AF (マクロン)
        """
        host_pattern = "[,.]"
        guest_pattern = "['¯]"
        host = re.findall(host_pattern, right)
        guest = (
            re.findall(guest_pattern, left)[::-1],
            re.findall(guest_pattern, right),
        )
        result = []
        if "," in right:
            for i, h in enumerate(host, 1):
                if h == ",":
                    result.append((self.host_note[0] + i, self.host_note[1]))
        if "'" in left:
            for i, g in enumerate(guest[0], 1):
                if g == "'":
                    result.append((self.guest_note[0] - i, self.guest_note[1]))
        if "'" in right:
            for i, g in enumerate(guest[1], 1):
                if g == "'":
                    result.append((self.guest_note[0] + i, self.guest_note[1]))
        return tuple(result)

    def get_root_pos_from_op(self, op: str) -> tuple[int, int]:
        """
        ## root音を決定する
        - 主音: O (Ah)
        - 右: ​> (Chy~)
        - 左: < (~Fu)
        - 客音から左: 𐑣 U+10463 (crana)
        - 客音から右: 𐑙 U+10459 (navra)
        """
        result = (0, 0)
        if "O" in op:
            pass
        elif ">" in op:
            result = (op.count(">"), result[1])
        elif "<" in op:
            result = (-op.count("<"), result[1])
        if "𐑣" in op:
            result = (
                self.guest_note[0] + result[0] - 1,
                self.guest_note[1] + result[1],
            )
        elif "𐑙" in op:
            result = (
                result[0] - self.guest_note[0] + 1,
                result[1] - self.guest_note[1],
            )
        return result

    def get_base_notes_from_op(self, op: str) -> tuple[tuple[int, int]]:
        """
        ## 形を作る
        - 主音抜き: - (ハイフン)
        - 司音抜き: U+0331 (下結合可能マクロン)
        - 客音抜き: U+0304 (結合可能マクロン)
        """
        result = []
        if "-" not in op:
            result.append(self.root)
        if "̱" not in op:
            result.append(self.host_note)
        if "̄" not in op:
            result.append(self.guest_note)
        return tuple(result)

    def point_to_ji(
        self,
        points: tuple[tuple[int, int], ...],
        octave: int,
        voicing: tuple[int, ...] | None = None,
    ) -> tuple[tuple[int, ...], ...]:
        result = []
        for p in points:
            base = [octave] + [0] * max(self.host_axis_index, self.guest_axis_index)
            base[self.host_axis_index] += p[0]
            base[self.guest_axis_index] += p[1]
            if voicing is not None and self.voicing_index < len(voicing):
                base[0] += voicing[self.voicing_index]
                self.voicing_index += 1
            result.append(tuple(base))
        return tuple(result)

    def get_ji_from_func(
        self,
        func: str,
        octave: int,
        voicing: tuple[int, ...] | None = None,
    ) -> tuple[tuple[int, ...], ...]:
        """
        ## 機能式からコード
        - ベース: /
        - 単発音: +
        ### 例:
        - Ahcrana u mas nu maskå mas kyxda-mas: 'O𐑣',.,
        - Schunavra u bylkå mas: <<𐑙',,
        """
        if func[0] == "/" or func[-1] == "\\":
            base = self.get_root_pos_from_op(func[1:] if func[0] == "/" else func[:-1])
            result = self.point_to_ji((base,), octave - 1, voicing)
        elif func[0] == "+":
            base = self.get_root_pos_from_op(func[1:])
            result = self.point_to_ji((base,), octave, voicing)
        else:
            match = re.match(
                r"^(['¯]*)(-?(?:[O0]|<+|>+)(?:̄?̱?|̱?̄?)[𐑣𐑙]?)([,'.¯]*)$", func
            )
            if not match:
                raise ValueError(f"invalid format: {func}")
            left, op, right = match.groups()
            op_to_def = self.get_base_notes_from_op(op)
            root_pos = self.get_root_pos_from_op(op)
            add_notes = self.get_add_from_sides(left, right)
            sum_chords = []
            for addend in op_to_def + add_notes:
                sum_chords.append((addend[0] + root_pos[0], addend[1] + root_pos[1]))
            result = self.point_to_ji(tuple(sum_chords), octave, voicing)
        return result
