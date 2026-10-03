"""
utils/tts.py
============
File này dùng để làm gì?
    Đọc văn bản thành tiếng (Text-to-Speech) cho chế độ Đánh vần, với 2 "backend":
      - pyttsx3 : offline, dùng giọng đọc có sẵn của hệ điều hành (Windows SAPI5).
                  Chỉ đọc được tiếng Việt nếu Windows có cài giọng tiếng Việt
                  (vd "Microsoft An" trong gói ngôn ngữ Vietnamese).
      - gTTS    : online (Google Text-to-Speech), đọc tiếng Việt tốt, cần Internet.
    Chế độ "auto": tiếng Việt -> pyttsx3 nếu có giọng Việt, nếu không -> gTTS.

Dữ liệu đi vào từ đâu?
    Văn bản từ gui/spelling_view.py (SpellingEngine.text).

Dữ liệu được xử lý như thế nào?
    Chạy trên thread nền (không làm đơ giao diện). gTTS tạo file mp3 tạm rồi phát
    bằng Windows MCI (winmm, có sẵn trong Windows - không cần thư viện thêm);
    trên macOS/Linux dùng afplay/mpg123/ffplay nếu có.

Dữ liệu được truyền sang module nào?
    Không truyền đi; phát âm thanh ra loa. Lỗi được trả qua callback để GUI hiển thị.

Kết quả trả về ở đâu?
    Âm thanh; trạng thái qua thuộc tính is_speaking và callback on_done(error|None).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Callable, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

BACKENDS = ["auto", "pyttsx3", "gtts"]


class TTSError(Exception):
    """Không đọc được văn bản (thiếu thư viện, không có giọng, mất mạng...)."""


# ---------------------------------------------------------------- pyttsx3
def _pyttsx3_voices():
    import pyttsx3

    engine = pyttsx3.init()
    try:
        return engine, engine.getProperty("voices") or []
    except Exception:
        engine.stop()
        raise


def _voice_matches(voice, lang: str) -> bool:
    """Nhận biết giọng theo id/tên/ngôn ngữ, vd 'Microsoft An - Vietnamese (Vietnam)', 'vi_VN'."""
    import re

    text = " ".join(str(x) for x in (getattr(voice, "id", ""), getattr(voice, "name", ""),
                                      getattr(voice, "languages", ""))).lower()
    tokens = set(re.split(r"[^a-z0-9]+", text))
    if lang == "vi":
        return "vi" in tokens or "vietnam" in text or "vietnamese" in text
    return lang in tokens or "english" in text


def has_pyttsx3_voice(lang: str) -> bool:
    try:
        engine, voices = _pyttsx3_voices()
        engine.stop()
        return any(_voice_matches(v, lang) for v in voices)
    except Exception:
        return False


def _speak_pyttsx3(text: str, lang: str, rate: int) -> None:
    try:
        import pyttsx3  # noqa: F401
    except ImportError as exc:
        raise TTSError("pyttsx3 is not installed: python -m pip install pyttsx3") from exc
    try:
        engine, voices = _pyttsx3_voices()
    except Exception as exc:
        raise TTSError(f"Cannot start the system speech engine: {exc}") from exc
    try:
        voice = next((v for v in voices if _voice_matches(v, lang)), None)
        if voice is None and lang == "vi":
            raise TTSError("No Vietnamese voice installed in the operating system.")
        if voice is not None:
            engine.setProperty("voice", voice.id)
        engine.setProperty("rate", rate)
        engine.say(text)
        engine.runAndWait()
    finally:
        try:
            engine.stop()
        except Exception:
            pass


# ------------------------------------------------------------------- gTTS
def _play_mp3(path: str) -> None:
    if sys.platform.startswith("win"):
        import ctypes

        winmm = ctypes.windll.winmm
        alias = f"hsr_tts_{threading.get_ident()}"
        buf = ctypes.create_unicode_buffer(256)
        if winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', buf, 255, None) != 0:
            raise TTSError("Cannot open audio device (Windows MCI).")
        try:
            winmm.mciSendStringW(f"play {alias} wait", buf, 255, None)
        finally:
            winmm.mciSendStringW(f"close {alias}", buf, 255, None)
        return
    for cmd in (["afplay", path], ["mpg123", "-q", path],
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, check=False)
            return
    raise TTSError("No audio player found (install mpg123 or ffmpeg).")


def _speak_gtts(text: str, lang: str) -> None:
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise TTSError("gTTS is not installed: python -m pip install gTTS") from exc
    fd, path = tempfile.mkstemp(suffix=".mp3", prefix="hsr_tts_")
    os.close(fd)
    try:
        try:
            gTTS(text=text, lang=lang).save(path)
        except Exception as exc:
            raise TTSError(f"Online speech (gTTS) failed - check the Internet connection: {exc}") from exc
        _play_mp3(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


# ------------------------------------------------------------------ class
class TextToSpeech:
    def __init__(self, backend: str = "auto", lang: str = "vi", rate: int = 170) -> None:
        self.backend = backend if backend in BACKENDS else "auto"
        self.lang = lang
        self.rate = rate
        self._thread: Optional[threading.Thread] = None

    @property
    def is_speaking(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _order(self) -> List[str]:
        if self.backend != "auto":
            return [self.backend]
        if self.lang == "vi" and not has_pyttsx3_voice("vi"):
            return ["gtts", "pyttsx3"]
        return ["pyttsx3", "gtts"]

    def speak_blocking(self, text: str) -> str:
        """Đọc và chờ xong. Trả tên backend đã dùng; ném TTSError nếu mọi backend lỗi."""
        text = (text or "").strip()
        if not text:
            raise TTSError("Nothing to speak.")
        errors = []
        for name in self._order():
            try:
                if name == "pyttsx3":
                    _speak_pyttsx3(text, self.lang, self.rate)
                else:
                    _speak_gtts(text, self.lang)
                logger.info("Spoke %d chars with %s", len(text), name)
                return name
            except TTSError as exc:
                logger.warning("TTS backend %s failed: %s", name, exc)
                errors.append(f"{name}: {exc}")
        raise TTSError("\n".join(errors))

    def speak(self, text: str, on_done: Optional[Callable[[Optional[str]], None]] = None) -> bool:
        """Đọc trên thread nền. on_done(None) khi thành công, on_done(error) khi lỗi.
        Trả False nếu đang đọc dở câu trước."""
        if self.is_speaking:
            return False

        def worker():
            err = None
            try:
                self.speak_blocking(text)
            except TTSError as exc:
                err = str(exc)
            except Exception as exc:  # không để lỗi lạ làm chết thread
                logger.exception("TTS crashed")
                err = f"Unexpected TTS error: {exc}"
            if on_done:
                on_done(err)

        self._thread = threading.Thread(target=worker, name="TTS", daemon=True)
        self._thread.start()
        return True
