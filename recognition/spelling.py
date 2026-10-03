"""
recognition/spelling.py
=======================
File này dùng để làm gì?
    Lõi của chế độ ĐÁNH VẦN (giai đoạn 2):
      1. VietnameseComposer: ghép chữ cái + dấu phụ (mũ ^, móc/râu ’, trăng ˘)
         + dấu thanh (sắc, huyền, hỏi, ngã, nặng) theo quy tắc chính tả tiếng Việt.
      2. SpellingEngine: biến chuỗi kết quả nhận diện theo thời gian thành văn bản:
         giữ ký hiệu ổn định đủ lâu -> "chốt" ký hiệu -> thêm vào câu; tự thêm
         khoảng trắng khi hạ tay; xử lý ký hiệu điều khiển (cách, xóa, đọc).

Dữ liệu đi vào từ đâu?
    - list[Prediction] mỗi frame (từ core.engine, qua gui/spelling_view.py).
    - Lệnh từ nút bấm / phím tắt trên giao diện (thêm dấu, xóa, cách...).

Dữ liệu được xử lý như thế nào?
    Mỗi nhãn (label) được phân loại theo tiền tố:
        letter_x   -> chữ cái x          (vd letter_a, letter_dd = đ)
        mark_xxx   -> dấu phụ / dấu thanh (mark_mu, mark_rau, mark_trang, mark_sac...)
        ctrl_xxx   -> lệnh điều khiển     (ctrl_space, ctrl_delete, ctrl_speak, ctrl_clear)
        còn lại    -> một từ/cụm từ      (theo bảng PHRASES hoặc tên hiển thị)
    Dấu thanh được đặt đúng nguyên âm theo quy tắc chính tả (kiểu truyền thống:
    hóa, thúy, khỏe), có xử lý "qu", "gi", "ươ", "uô", "iê"...

Dữ liệu được truyền sang module nào?
    Văn bản -> gui/spelling_view.py (hiển thị) -> utils/tts.py (đọc thành tiếng).

Kết quả trả về ở đâu?
    SpellingEngine.text, SpellingEngine.state() và các sự kiện (events) trả về từ update().
"""
from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from utils.constants import display_gesture

# ============================================================================
# 1. Bảng nguyên âm và dấu thanh
# ============================================================================
TONES = ["", "sac", "huyen", "hoi", "nga", "nang"]
TONE_SYMBOLS = {"sac": "´", "huyen": "`", "hoi": "̉", "nga": "~", "nang": "."}
TONE_NAMES_VI = {"sac": "sắc", "huyen": "huyền", "hoi": "hỏi", "nga": "ngã", "nang": "nặng", "": "không dấu"}

# nguyên âm gốc -> [không dấu, sắc, huyền, hỏi, ngã, nặng]
_VOWEL_TABLE = {
    "a": "aáàảãạ", "ă": "ăắằẳẵặ", "â": "âấầẩẫậ",
    "e": "eéèẻẽẹ", "ê": "êếềểễệ",
    "i": "iíìỉĩị",
    "o": "oóòỏõọ", "ô": "ôốồổỗộ", "ơ": "ơớờởỡợ",
    "u": "uúùủũụ", "ư": "ưứừửữự",
    "y": "yýỳỷỹỵ",
}
# ký tự có dấu -> (nguyên âm gốc, tên thanh)
_DECOMPOSE: Dict[str, Tuple[str, str]] = {}
for _base, _forms in _VOWEL_TABLE.items():
    for _i, _ch in enumerate(_forms):
        _DECOMPOSE[_ch] = (_base, TONES[_i])
        _DECOMPOSE[_ch.upper()] = (_base.upper(), TONES[_i])

_SPECIAL_VOWELS = set("ăâêôơư")
# dấu phụ: nguyên âm gốc -> nguyên âm mới
_MARK_MAP = {
    "mu": {"a": "â", "e": "ê", "o": "ô"},      # ^  (dấu mũ)
    "rau": {"o": "ơ", "u": "ư"},              # ’  (dấu móc / râu)
    "trang": {"a": "ă"},                      # ˘  (dấu trăng)
}
MARK_NAMES_VI = {"mu": "mũ (^)", "rau": "móc/râu (’)", "trang": "trăng (˘)"}


def split_char(ch: str) -> Tuple[str, str]:
    """'ế' -> ('ê', 'sac'); 'b' -> ('b', '')."""
    return _DECOMPOSE.get(ch, (ch, ""))


def make_char(base: str, tone: str) -> str:
    upper = base.isupper()
    forms = _VOWEL_TABLE.get(base.lower())
    if not forms:
        return base
    ch = forms[TONES.index(tone)]
    return ch.upper() if upper else ch


def is_vowel(ch: str) -> bool:
    return split_char(ch)[0].lower() in _VOWEL_TABLE


class VietnameseComposer:
    """Các hàm thuần (không trạng thái) để ghép dấu cho MỘT từ tiếng Việt."""

    @staticmethod
    def _vowel_span(word: str) -> Tuple[int, int]:
        """Trả (start, end) của cụm nguyên âm chính trong từ (end không bao gồm)."""
        low = "".join(split_char(c)[0].lower() for c in word)
        start = 0
        # bỏ phụ âm đầu
        while start < len(low) and low[start] not in _VOWEL_TABLE:
            start += 1
        # "qu": u thuộc phụ âm đầu; "gi" + nguyên âm: i thuộc phụ âm đầu
        if start > 0 and low[start - 1] == "q" and start < len(low) and low[start] == "u":
            start += 1
        elif start > 0 and low[start - 1] == "g" and low[start:start + 1] == "i" \
                and start + 1 < len(low) and low[start + 1] in _VOWEL_TABLE:
            start += 1
        end = start
        while end < len(low) and low[end] in _VOWEL_TABLE:
            end += 1
        return start, end

    @classmethod
    def tone_position(cls, word: str) -> Optional[int]:
        """Vị trí nguyên âm nhận dấu thanh (quy tắc chính tả kiểu truyền thống)."""
        start, end = cls._vowel_span(word)
        if start >= end:
            # trường hợp chỉ có "gi"/"qu" + không còn nguyên âm: vd "gì"
            for i in range(len(word) - 1, -1, -1):
                if is_vowel(word[i]):
                    return i
            return None
        bases = [split_char(c)[0].lower() for c in word[start:end]]
        # 1) Có nguyên âm mang dấu phụ (ă â ê ô ơ ư) -> đặt vào đó ("ươ" -> ơ)
        special = [i for i, b in enumerate(bases) if b in _SPECIAL_VOWELS]
        if special:
            return start + special[-1]
        n = len(bases)
        if n == 1:
            return start
        # 2) Có phụ âm cuối -> nguyên âm cuối của cụm (hoán, toán, muốn)
        if end < len(word):
            return end - 1
        # 3) Vần mở: 3 nguyên âm -> giữa (khoái, khuỷu); 2 nguyên âm -> đầu (hóa, múa, tái)
        return start + 1 if n == 3 else start

    @classmethod
    def apply_tone(cls, word: str, tone: str) -> str:
        if tone not in TONES:
            raise ValueError(f"Unknown tone: {tone}")
        # bỏ thanh cũ ở mọi nguyên âm
        chars = [make_char(split_char(c)[0], "") if is_vowel(c) else c for c in word]
        plain = "".join(chars)
        pos = cls.tone_position(plain)
        if pos is None:
            return word
        chars[pos] = make_char(split_char(chars[pos])[0], tone)
        return "".join(chars)

    @classmethod
    def current_tone(cls, word: str) -> str:
        for c in word:
            base, tone = split_char(c)
            if tone:
                return tone
        return ""

    @classmethod
    def apply_mark(cls, word: str, mark: str) -> str:
        """Thêm dấu phụ vào nguyên âm phù hợp GẦN CUỐI từ nhất (giữ nguyên dấu thanh)."""
        mapping = _MARK_MAP.get(mark)
        if not mapping:
            raise ValueError(f"Unknown mark: {mark}")
        tone = cls.current_tone(word)
        chars = [make_char(split_char(c)[0], "") if is_vowel(c) else c for c in word]
        low = [c.lower() for c in chars]
        # đặc biệt: "uo" + râu -> "ươ" (người, trường)
        if mark == "rau":
            for i in range(len(low) - 1, 0, -1):
                if low[i - 1] == "u" and low[i] == "o":
                    chars[i - 1] = "Ư" if chars[i - 1].isupper() else "ư"
                    chars[i] = "Ơ" if chars[i].isupper() else "ơ"
                    return cls.apply_tone("".join(chars), tone) if tone else "".join(chars)
        for i in range(len(low) - 1, -1, -1):
            if low[i] in mapping:
                new = mapping[low[i]]
                chars[i] = new.upper() if chars[i].isupper() else new
                result = "".join(chars)
                return cls.apply_tone(result, tone) if tone else result
        return word  # không có nguyên âm phù hợp -> giữ nguyên


# ============================================================================
# 2. Phân loại nhãn
# ============================================================================
CONTROL_LABELS = {"ctrl_space", "ctrl_delete", "ctrl_speak", "ctrl_clear"}

# Cụm từ DEMO cho các gesture có sẵn của MediaPipe. Đây KHÔNG phải nghĩa trong
# ngôn ngữ ký hiệu Việt Nam; chỉ để thử nghiệm chế độ ghép câu khi chưa train.
# Có thể sửa trong file này hoặc thêm gesture mới bằng màn hình Dataset.
PHRASES: Dict[str, Dict[str, str]] = {
    "open_palm": {"vi": "xin chào", "en": "hello"},
    "thumb_up": {"vi": "tốt", "en": "good"},
    "thumb_down": {"vi": "không tốt", "en": "not good"},
    "victory": {"vi": "chiến thắng", "en": "victory"},
    "pointing_up": {"vi": "chú ý", "en": "attention"},
    "closed_fist": {"vi": "dừng lại", "en": "stop"},
    "i_love_you": {"vi": "tôi yêu bạn", "en": "I love you"},
}

VSL_LETTERS = ["a", "b", "c", "d", "dd", "e", "g", "h", "i", "k", "l", "m", "n",
               "o", "p", "q", "r", "s", "t", "u", "v", "x", "y"]
VSL_STATIC_MARKS = ["mu", "rau"]          # tĩnh theo chuẩn (có thể train bằng camera)
DYNAMIC_MARKS = ["trang", "sac", "huyen", "hoi", "nga", "nang"]  # cần chuyển động -> nút/phím


def letter_label(letter: str) -> str:
    return f"letter_{letter}"


def classify_label(label: str) -> Tuple[str, str]:
    """-> (loại, giá trị). loại: letter | mark | tone | control | phrase."""
    if label.startswith("letter_"):
        val = label[len("letter_"):]
        return "letter", "đ" if val == "dd" else val
    if label.startswith("mark_"):
        val = label[len("mark_"):]
        if val in _MARK_MAP:
            return "mark", val
        if val in TONES and val:
            return "tone", val
        if val in ("none", "khong"):
            return "tone", ""
        return "phrase", val
    if label in CONTROL_LABELS:
        return "control", label[len("ctrl_"):]
    return "phrase", label


def phrase_for(label: str, lang: str = "vi",
               resolver: Optional[Callable[[str], Optional[str]]] = None) -> str:
    """Từ/cụm từ được thêm vào câu cho một gesture thông thường.
    Thứ tự ưu tiên: bảng PHRASES -> tên hiển thị người dùng đặt (resolver, vd "Cảm ơn")
    -> tên hiển thị mặc định."""
    if label in PHRASES:
        return PHRASES[label].get(lang) or PHRASES[label]["en"]
    if resolver is not None:
        try:
            name = resolver(label)
        except Exception:
            name = None
        if name:
            return name.strip().lower()
    return display_gesture(label, lang).lower()


# ============================================================================
# 3. Bộ máy đánh vần
# ============================================================================
@dataclass
class SpellingEvent:
    kind: str            # commit | space | delete | clear | speak | tone | mark | ignored
    label: str = ""
    text: str = ""
    message: str = ""


@dataclass
class SpellingState:
    candidate: Optional[str]
    progress: float          # 0..1 tiến độ giữ ký hiệu
    confidence: float
    text: str
    current_word: str
    waiting_release: bool
    hand_present: bool
    history: List[str] = field(default_factory=list)


class SpellingEngine:
    """Chuyển chuỗi dự đoán theo thời gian thành văn bản tiếng Việt.

    Quy tắc:
      - Giữ một ký hiệu ổn định >= hold_time giây -> chốt ký hiệu.
      - Sau khi chốt phải đổi ký hiệu khác hoặc hạ tay mới chốt lại được
        (tránh lặp chữ). Muốn gõ 2 chữ giống nhau liên tiếp: hạ tay rồi giơ lại.
      - Không thấy tay trong auto_space giây sau khi vừa gõ chữ -> tự thêm khoảng trắng
        (0 = tắt).
    """

    def __init__(self, hold_time: float = 1.0, auto_space: float = 1.5, lang: str = "vi",
                 clock: Callable[[], float] = time.monotonic,
                 phrase_resolver: Optional[Callable[[str], Optional[str]]] = None) -> None:
        self.phrase_resolver = phrase_resolver
        self.hold_time = max(0.1, float(hold_time))
        self.auto_space = max(0.0, float(auto_space))
        self.lang = lang
        self._clock = clock
        self.text = ""
        self._undo: List[str] = []
        self._candidate: Optional[str] = None
        self._candidate_conf = 0.0
        self._candidate_since = 0.0
        self._committed_label: Optional[str] = None   # nhãn vừa chốt, chờ thả
        self._last_hand_time = clock()
        self._pending_space = False
        self.history: List[str] = []                   # các nhãn đã chốt (để hiển thị)

    # ---------------------------------------------------------------- text
    @property
    def current_word(self) -> str:
        if not self.text or self.text[-1] == " ":
            return ""
        return self.text.split(" ")[-1]

    def _replace_current_word(self, new_word: str) -> None:
        old = self.current_word
        self.text = self.text[: len(self.text) - len(old)] + new_word

    def _push_undo(self) -> None:
        self._undo.append(self.text)
        if len(self._undo) > 200:
            self._undo.pop(0)

    # ------------------------------------------------------------ actions
    def add_letter(self, letter: str) -> SpellingEvent:
        self._push_undo()
        self.text += letter
        self._pending_space = True
        return SpellingEvent("commit", text=letter)

    def add_phrase(self, phrase: str) -> SpellingEvent:
        self._push_undo()
        if self.text and not self.text.endswith(" "):
            self.text += " "
        self.text += phrase + " "
        self._pending_space = False
        return SpellingEvent("commit", text=phrase)

    def apply_mark(self, mark: str) -> SpellingEvent:
        word = self.current_word
        if not word:
            return SpellingEvent("ignored", message="Type a letter before adding a diacritic.")
        new = VietnameseComposer.apply_mark(word, mark)
        if new == word:
            return SpellingEvent("ignored", message="No suitable vowel for this diacritic.")
        self._push_undo()
        self._replace_current_word(new)
        return SpellingEvent("mark", text=new)

    def apply_tone(self, tone: str) -> SpellingEvent:
        word = self.current_word
        if not word:
            return SpellingEvent("ignored", message="Type a word before adding a tone mark.")
        if not any(is_vowel(c) for c in word):
            return SpellingEvent("ignored", message="The current word has no vowel.")
        self._push_undo()
        self._replace_current_word(VietnameseComposer.apply_tone(word, tone))
        return SpellingEvent("tone", text=self.current_word)

    def space(self) -> SpellingEvent:
        self._pending_space = False
        if not self.text or self.text.endswith(" "):
            return SpellingEvent("ignored")
        self._push_undo()
        self.text += " "
        return SpellingEvent("space")

    def backspace(self) -> SpellingEvent:
        if not self.text:
            return SpellingEvent("ignored")
        self._push_undo()
        self.text = self.text[:-1]
        return SpellingEvent("delete")

    def undo(self) -> SpellingEvent:
        if not self._undo:
            return SpellingEvent("ignored")
        self.text = self._undo.pop()
        return SpellingEvent("delete")

    def clear(self) -> SpellingEvent:
        if self.text:
            self._push_undo()
        self.text = ""
        self.history.clear()
        self._pending_space = False
        return SpellingEvent("clear")

    def set_text(self, text: str) -> None:
        if text != self.text:
            self._push_undo()
            self.text = text

    def execute_label(self, label: str) -> SpellingEvent:
        kind, value = classify_label(label)
        if kind == "letter":
            ev = self.add_letter(value)
        elif kind == "mark":
            ev = self.apply_mark(value)
        elif kind == "tone":
            ev = self.apply_tone(value)
        elif kind == "control":
            ev = {"space": self.space, "delete": self.backspace, "clear": self.clear,
                  "speak": lambda: SpellingEvent("speak", text=self.text.strip())}[value]()
        else:
            ev = self.add_phrase(phrase_for(label, self.lang, self.phrase_resolver))
        ev.label = label
        if ev.kind != "ignored":
            self.history.append(label)
            self.history[:] = self.history[-30:]
        return ev

    # ------------------------------------------------------------- stream
    def update(self, predictions, now: Optional[float] = None) -> List[SpellingEvent]:
        """Gọi mỗi frame với list[Prediction]. Trả các sự kiện phát sinh."""
        now = self._clock() if now is None else now
        events: List[SpellingEvent] = []
        accepted = [p for p in predictions if getattr(p, "accepted", False) and p.gesture]
        best = max(accepted, key=lambda p: p.confidence) if accepted else None
        label = best.gesture if best else None

        if predictions:
            self._last_hand_time = now
        elif self._pending_space and self.auto_space > 0 and now - self._last_hand_time >= self.auto_space - 1e-6:
            events.append(self.space())

        if not predictions:
            # hạ tay -> cho phép chốt lại cùng ký hiệu
            self._committed_label = None

        if label != self._candidate:
            self._candidate = label
            self._candidate_since = now
            if label != self._committed_label:
                self._committed_label = None
        self._candidate_conf = best.confidence if best else 0.0

        if label and label != self._committed_label and now - self._candidate_since >= self.hold_time - 1e-6:
            events.append(self.execute_label(label))
            self._committed_label = label
        return [e for e in events if e.kind != "ignored" or e.message]

    def state(self, now: Optional[float] = None) -> SpellingState:
        now = self._clock() if now is None else now
        waiting = self._candidate is not None and self._candidate == self._committed_label
        progress = 0.0
        if self._candidate and not waiting:
            progress = min(1.0, (now - self._candidate_since) / self.hold_time)
        return SpellingState(
            candidate=self._candidate, progress=progress, confidence=self._candidate_conf,
            text=self.text, current_word=self.current_word, waiting_release=waiting,
            hand_present=(now - self._last_hand_time) < 0.3, history=list(self.history),
        )


def normalize_text(text: str) -> str:
    """Chuẩn hóa Unicode NFC (tránh lỗi hiển thị/đọc khi chữ có dấu tổ hợp)."""
    return unicodedata.normalize("NFC", text)
