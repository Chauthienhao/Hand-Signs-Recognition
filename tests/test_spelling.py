"""
tests/test_spelling.py
======================
File này dùng để làm gì?
    Kiểm thử tự động cho chế độ Đánh vần (không cần camera, không phát âm thật):
      1. VietnameseComposer: đặt dấu thanh + dấu phụ đúng chính tả.
      2. SpellingEngine: giữ -> chốt, chống lặp, tự thêm khoảng trắng, ngưỡng tin cậy,
         cụm từ, lệnh điều khiển.
      3. TextToSpeech: chọn backend và tự chuyển sang backend dự phòng khi lỗi.

Dữ liệu đi vào từ đâu?
    Dữ liệu giả lập ngay trong file (danh sách từ, chuỗi dự đoán theo thời gian giả).

Dữ liệu được xử lý như thế nào?
    So sánh kết quả thực tế với kết quả mong đợi; đếm số ca lỗi.

Dữ liệu được truyền sang module nào?
    Không truyền đi.

Kết quả trả về ở đâu?
    In ra màn hình; mã thoát 0 = tất cả đạt, 1 = có lỗi.

Chạy:
    python -m tests.test_spelling
"""
from __future__ import annotations

import os
import sys
import threading
from types import SimpleNamespace as NS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from recognition.spelling import SpellingEngine, VietnameseComposer as V  # noqa: E402

FAILURES = []


def check(name, actual, expected):
    if actual != expected:
        FAILURES.append(name)
        print(f"  [FAIL] {name}: got {actual!r}, expected {expected!r}")


def test_tones():
    cases = [
        ("hoa", "sac", "hóa"), ("mua", "sac", "múa"), ("tai", "sac", "tái"), ("toan", "sac", "toán"),
        ("qua", "huyen", "quà"), ("gia", "huyen", "già"), ("gi", "huyen", "gì"), ("tuy", "sac", "túy"),
        ("khoai", "sac", "khoái"), ("ngươi", "huyen", "người"), ("muôn", "sac", "muốn"),
        ("tiêu", "sac", "tiếu"), ("cưu", "sac", "cứu"), ("viêt", "nang", "việt"), ("Viêt", "nang", "Việt"),
        ("hóa", "huyen", "hòa"), ("thuơ", "hoi", "thuở"), ("khuyu", "hoi", "khuỷu"), ("a", "nga", "ã"),
        ("quyên", "huyen", "quyền"), ("giương", "sac", "giướng"), ("chao", "huyen", "chào"),
        ("lua", "sac", "lúa"), ("ca", "hoi", "cả"), ("ga", "nga", "gã"), ("ta", "nang", "tạ"),
        ("cá", "", "ca"),
    ]
    for word, tone, exp in cases:
        check(f"tone {word}+{tone}", V.apply_tone(word, tone), exp)
    return len(cases)


def test_marks():
    cases = [
        ("a", "mu", "â"), ("viet", "mu", "viêt"), ("nguoi", "rau", "ngươi"), ("tu", "rau", "tư"),
        ("o", "rau", "ơ"), ("a", "trang", "ă"), ("toi", "mu", "tôi"), ("ná", "mu", "nấ"),
        ("truong", "rau", "trương"), ("b", "mu", "b"), ("vạy", "mu", "vậy"),
    ]
    for word, mark, exp in cases:
        check(f"mark {word}+{mark}", V.apply_mark(word, mark), exp)
    return len(cases)


def test_engine():
    t = [0.0]
    eng = SpellingEngine(hold_time=1.0, auto_space=1.5, clock=lambda: t[0])

    def pred(label, conf=0.9, accepted=True):
        return [NS(gesture=label, confidence=conf, accepted=accepted)]

    def hold(label, secs=1.5, **kw):
        for _ in range(int(secs / 0.1)):
            t[0] += 0.1
            eng.update(pred(label, **kw) if label else [])

    # "việt nam": chữ bằng camera, dấu bằng nút, hạ tay -> tự cách
    for lbl in ("letter_v", "letter_i", "letter_e"):
        hold(lbl)
    eng.apply_mark("mu")
    hold("letter_t")
    eng.apply_tone("nang")
    hold(None, 2.0)
    for lbl in ("letter_n", "letter_a", "letter_m"):
        hold(lbl)
    check("engine viet nam", eng.text, "việt nam")

    eng.clear()
    hold("letter_o", 3.0)
    check("no repeat while holding", eng.text, "o")
    hold(None, 0.3)
    hold("letter_o")
    check("repeat after release", eng.text, "oo")

    eng.clear()
    hold("letter_a", 2.0, conf=0.3, accepted=False)
    check("low confidence ignored", eng.text, "")

    eng.clear()
    hold("i_love_you")
    hold("thumb_up")
    hold("ctrl_delete")
    check("phrases + ctrl_delete", eng.text, "tôi yêu bạn tốt")
    check("undo", (eng.undo(), eng.text)[1], "tôi yêu bạn tốt ")

    eng.clear()
    hold("letter_dd")
    hold("letter_a")
    eng.apply_tone("huyen")
    check("letter đ", eng.text, "đà")
    return 7


def test_tts():
    import utils.tts as T

    spoken = []
    orig_py, orig_g = T._speak_pyttsx3, T._speak_gtts
    try:
        T._speak_pyttsx3 = lambda text, lang, rate: (_ for _ in ()).throw(T.TTSError("no voice"))
        T._speak_gtts = lambda text, lang: spoken.append((text, lang))
        tts = T.TextToSpeech("auto", "vi")
        check("tts fallback", tts.speak_blocking("xin chào"), "gtts")
        done, res = threading.Event(), {}
        tts.speak("việt nam", lambda err: (res.setdefault("err", err), done.set()))
        done.wait(3)
        check("tts async", res.get("err", "timeout"), None)
        check("tts text", spoken[-1], ("việt nam", "vi"))
        check("voice detect vi", T._voice_matches(NS(id="TTS_MS_VI-VN_AN", name="Microsoft An - Vietnamese (Vietnam)",
                                                     languages=[]), "vi"), True)
        check("voice detect en≠vi", T._voice_matches(NS(id="TTS_MS_EN-US_ZIRA", name="Microsoft Zira - English",
                                                        languages=[]), "vi"), False)
    finally:
        T._speak_pyttsx3, T._speak_gtts = orig_py, orig_g
    return 5


def main() -> int:
    total = 0
    for fn in (test_tones, test_marks, test_engine, test_tts):
        n = fn()
        total += n
        print(f"{fn.__name__:<12} {n} cases")
    print("-" * 40)
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}/{total}")
        return 1
    print(f"ALL {total} CASES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
