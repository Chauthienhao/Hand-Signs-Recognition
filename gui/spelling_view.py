"""
gui/spelling_view.py
====================
File này dùng để làm gì?
    Màn hình ĐÁNH VẦN (giai đoạn 2): người dùng làm ký hiệu chữ cái trước camera,
    hệ thống ghép thành từ/câu tiếng Việt có dấu và đọc thành tiếng.
    Bên trái: camera + ký hiệu hiện tại + thanh "giữ" (hold). Bên phải: câu đang
    soạn, nút dấu phụ / dấu thanh, nút Cách / Xóa / Hoàn tác / Đọc / Sao chép / Lưu.

Dữ liệu đi vào từ đâu?
    - FrameResult từ core.engine (MainWindow gọi on_frame mỗi khi có frame mới).
    - Nút bấm, phím tắt, chỉnh sửa trực tiếp trong ô văn bản.
    - Thiết lập spelling_hold_time, spelling_auto_space, tts_backend, tts_lang (Settings).

Dữ liệu được xử lý như thế nào?
    list[Prediction] -> recognition/spelling.py (SpellingEngine.update) -> sự kiện
    (chốt chữ, cách, xóa, đọc) -> cập nhật ô văn bản. Dấu cần chuyển động theo chuẩn
    NNKH (dấu trăng và 5 dấu thanh) được nhập bằng nút hoặc phím tắt Ctrl+1..8.

Dữ liệu được truyền sang module nào?
    utils/tts.py (đọc thành tiếng), clipboard hệ điều hành, file .txt.

Kết quả trả về ở đâu?
    Ô văn bản trên màn hình, âm thanh, clipboard hoặc file .txt.
"""
from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from gui.camera_view import CameraView
from gui.common import BasePage, title_label
from recognition.spelling import (
    SpellingEngine, TONE_NAMES_VI, VSL_LETTERS, letter_label, normalize_text,
)
from utils.constants import display_gesture, tr
from utils.helpers import file_stamp
from utils.logger import get_logger
from utils.tts import TextToSpeech

logger = get_logger(__name__)

# (nhãn nút, hàm áp dụng, phím tắt)
TONE_BUTTONS = [("´ sắc", "sac", "1"), ("` huyền", "huyen", "2"), ("? hỏi", "hoi", "3"),
                ("~ ngã", "nga", "4"), (". nặng", "nang", "5"), ("bỏ dấu", "", "0")]
MARK_BUTTONS = [("^ mũ", "mu", "6"), ("’ râu", "rau", "7"), ("˘ trăng", "trang", "8")]


class SpellingView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        s = app.settings
        repo = getattr(app.dataset_manager, "gesture_repo", None)
        self.engine = SpellingEngine(s.get("spelling_hold_time"), s.get("spelling_auto_space"),
                                     lang=s.get("tts_lang"),
                                     phrase_resolver=repo.display_name if repo else None)
        self.tts = TextToSpeech(s.get("tts_backend"), s.get("tts_lang"))
        self._tts_result: Optional[str] = None
        self._tts_pending = False
        self._shown_text = None

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2, minsize=420)
        self.grid_rowconfigure(1, weight=1)
        title_label(self, tr("Spelling Mode")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        # ------------------------------------------------------------ trái
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        self.camera_view = CameraView(left)
        self.camera_view.grid(row=0, column=0, sticky="nsew")

        status = ctk.CTkFrame(left)
        status.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        status.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(status, text=tr("Current sign"), text_color="gray60").grid(row=0, column=0, padx=12, pady=(8, 0), sticky="w")
        self.sign_lbl = ctk.CTkLabel(status, text="---", font=ctk.CTkFont(size=26, weight="bold"), anchor="w")
        self.sign_lbl.grid(row=1, column=0, columnspan=2, padx=12, sticky="w")
        self.hold_bar = ctk.CTkProgressBar(status)
        self.hold_bar.set(0)
        self.hold_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=6)
        self.hint_lbl = ctk.CTkLabel(status, text="", text_color=("#e65100", "#ffa726"), anchor="w")
        self.hint_lbl.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text=tr("Start"), fg_color="#2e7d32", hover_color="#1b5e20",
                      command=app.start_camera).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(btns, text=tr("Stop"), fg_color="#c62828", hover_color="#8e0000",
                      command=app.stop_camera).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # ------------------------------------------------------------- phải
        right = ctk.CTkScrollableFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        right.grid_columnconfigure(0, weight=1)

        title_label(right, tr("Sentence"), 16).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.textbox = ctk.CTkTextbox(right, height=130, wrap="word", font=ctk.CTkFont(size=22))
        self.textbox.grid(row=1, column=0, sticky="ew", padx=8)
        self.textbox.bind("<KeyRelease>", self._on_text_edited)

        row = self._button_row(right, 2, [(tr("Space"), self._space), (tr("Backspace"), self._backspace),
                                          (tr("Undo"), self._undo), (tr("Clear"), self._clear)])
        ctk.CTkLabel(right, text=tr("Diacritics"), text_color="gray60").grid(row=row, column=0, sticky="w", padx=8, pady=(8, 0))
        row = self._button_row(right, row + 1, [(f"{lbl}  (Ctrl+{key})", lambda m=m: self._mark(m))
                                                for lbl, m, key in MARK_BUTTONS] + [("đ", lambda: self._letter("đ"))])
        ctk.CTkLabel(right, text=tr("Tones"), text_color="gray60").grid(row=row, column=0, sticky="w", padx=8, pady=(8, 0))
        row = self._button_row(right, row + 1, [(f"{lbl} ({key})", lambda t=t: self._tone(t))
                                                for lbl, t, key in TONE_BUTTONS[:3]])
        row = self._button_row(right, row, [(f"{lbl} ({key})", lambda t=t: self._tone(t))
                                            for lbl, t, key in TONE_BUTTONS[3:]])

        self.speak_btn = ctk.CTkButton(right, text="🔊  " + tr("Speak") + "  (Enter)", height=40,
                                       fg_color="#6a1b9a", hover_color="#4a148c", command=self._speak)
        self.speak_btn.grid(row=row, column=0, sticky="ew", padx=8, pady=(12, 4))
        row = self._button_row(right, row + 1, [(tr("Copy"), self._copy), (tr("Save .txt"), self._save)])

        ctk.CTkLabel(right, text=tr("Recent signs"), text_color="gray60").grid(row=row, column=0, sticky="w", padx=8, pady=(8, 0))
        self.history_lbl = ctk.CTkLabel(right, text="", anchor="w", justify="left", wraplength=380)
        self.history_lbl.grid(row=row + 1, column=0, sticky="ew", padx=8)

        # Thiết lập nhanh
        quick = ctk.CTkFrame(right)
        quick.grid(row=row + 2, column=0, sticky="ew", padx=8, pady=(10, 4))
        quick.grid_columnconfigure(1, weight=1)
        self.hold_lbl = ctk.CTkLabel(quick, text="")
        self.hold_lbl.grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.hold_slider = ctk.CTkSlider(quick, from_=0.3, to=2.5, number_of_steps=22, command=self._on_hold_change)
        self.hold_slider.grid(row=0, column=1, sticky="ew", padx=8)
        self.space_lbl = ctk.CTkLabel(quick, text="")
        self.space_lbl.grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.space_slider = ctk.CTkSlider(quick, from_=0, to=4, number_of_steps=16, command=self._on_space_change)
        self.space_slider.grid(row=1, column=1, sticky="ew", padx=8)

        self.info_lbl = ctk.CTkLabel(right, text="", text_color="gray60", wraplength=380, justify="left", anchor="w")
        self.info_lbl.grid(row=row + 3, column=0, sticky="ew", padx=8, pady=(6, 2))
        ctk.CTkLabel(right, text=f"{tr('Shortcuts')}: Enter = {tr('Speak')} · Ctrl+Space = {tr('Space')} · "
                                 f"Ctrl+Backspace · Ctrl+Z · Ctrl+0..5 = {tr('Tones')} · Ctrl+6/7/8 = ^ ’ ˘",
                     text_color="gray60", wraplength=380, justify="left", anchor="w").grid(
            row=row + 4, column=0, sticky="ew", padx=8, pady=(0, 8))

        self._load_quick_settings()
        self._bind_shortcuts()
        self._refresh_text()

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _button_row(parent, row: int, items) -> int:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        for i, (text, cmd) in enumerate(items):
            frame.grid_columnconfigure(i, weight=1)
            ctk.CTkButton(frame, text=text, height=32, command=cmd).grid(row=0, column=i, sticky="ew", padx=3)
        return row + 1

    def _bind_shortcuts(self) -> None:
        root = self.app

        def only_here(func):
            def handler(event=None):
                if self.app.current != "spelling":
                    return None
                # Enter trong ô văn bản = xuống dòng bình thường, không đọc
                if event is not None and event.keysym == "Return" and \
                        self.focus_get() is getattr(self.textbox, "_textbox", None):
                    return None
                func()
                return "break"
            return handler

        root.bind("<Return>", only_here(self._speak), add="+")
        root.bind("<Control-space>", only_here(self._space), add="+")
        root.bind("<Control-BackSpace>", only_here(self._backspace), add="+")
        root.bind("<Control-z>", only_here(self._undo), add="+")
        for _lbl, tone, key in TONE_BUTTONS:
            root.bind(f"<Control-Key-{key}>", only_here(lambda t=tone: self._tone(t)), add="+")
        for _lbl, mark, key in MARK_BUTTONS:
            root.bind(f"<Control-Key-{key}>", only_here(lambda m=mark: self._mark(m)), add="+")

    def _load_quick_settings(self) -> None:
        s = self.app.settings
        self.hold_slider.set(s.get("spelling_hold_time"))
        self.space_slider.set(s.get("spelling_auto_space"))
        self._on_hold_change(s.get("spelling_hold_time"), save=False)
        self._on_space_change(s.get("spelling_auto_space"), save=False)
        self.tts.backend = s.get("tts_backend")
        self.tts.lang = self.engine.lang = s.get("tts_lang")

    def _on_hold_change(self, value, save: bool = True) -> None:
        value = round(float(value), 1)
        self.engine.hold_time = max(0.1, value)
        self.hold_lbl.configure(text=f"{tr('Hold time (s)')}: {value:.1f}")
        if save:
            self.app.settings.set("spelling_hold_time", value)

    def _on_space_change(self, value, save: bool = True) -> None:
        value = round(float(value), 2)
        self.engine.auto_space = value
        self.space_lbl.configure(text=f"{tr('Auto space (s)')}: {value:.1f}" if value else
                                 f"{tr('Auto space (s)')}: off")
        if save:
            self.app.settings.set("spelling_auto_space", value)

    def _refresh_text(self) -> None:
        text = self.engine.text
        if text != self._shown_text:
            self._shown_text = text
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", text)
            self.textbox.see("end")
        self.history_lbl.configure(text="  ".join(display_gesture(l) for l in self.engine.history[-12:]) or "—")

    def _on_text_edited(self, _event=None) -> None:
        text = normalize_text(self.textbox.get("1.0", "end-1c"))
        self._shown_text = text
        self.engine.set_text(text)

    # ------------------------------------------------------------ actions
    def _after_action(self, event) -> None:
        if event.kind == "ignored" and event.message:
            self.hint_lbl.configure(text=event.message)
        self._refresh_text()

    def _space(self):
        self._after_action(self.engine.space())

    def _backspace(self):
        self._after_action(self.engine.backspace())

    def _undo(self):
        self._after_action(self.engine.undo())

    def _clear(self):
        self._after_action(self.engine.clear())

    def _mark(self, mark: str):
        self._after_action(self.engine.apply_mark(mark))

    def _tone(self, tone: str):
        self._after_action(self.engine.apply_tone(tone))

    def _letter(self, letter: str):
        self._after_action(self.engine.add_letter(letter))

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.engine.text.strip())
        self.hint_lbl.configure(text=tr("Copied"))

    def _save(self):
        if not self.engine.text.strip():
            messagebox.showwarning(tr("Warning"), tr("Nothing to speak"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")],
                                            initialfile=f"spelling_{file_stamp()}.txt")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.engine.text.strip() + "\n")
                self.hint_lbl.configure(text=f"{tr('Saved')}: {path}")
            except OSError as exc:
                messagebox.showerror(tr("Error"), str(exc))

    def _speak(self, text: Optional[str] = None):
        text = (text if text is not None else self.engine.text).strip()
        if not text:
            self.hint_lbl.configure(text=tr("Nothing to speak"))
            return
        self.tts.backend = self.app.settings.get("tts_backend")
        self.tts.lang = self.app.settings.get("tts_lang")

        def done(err):
            self._tts_result = err or ""   # chỉ ghi biến; GUI đọc trong _poll_tts

        if self.tts.speak(normalize_text(text), done):
            self._tts_pending = True
            self.speak_btn.configure(state="disabled", text="🔊  " + tr("Speaking..."))
            self.after(200, self._poll_tts)

    def _poll_tts(self):
        if self._tts_result is None:
            self.after(200, self._poll_tts)
            return
        err, self._tts_result, self._tts_pending = self._tts_result, None, False
        self.speak_btn.configure(state="normal", text="🔊  " + tr("Speak") + "  (Enter)")
        if err:
            messagebox.showerror(tr("Speech error"), err)

    # --------------------------------------------------------------- hooks
    def on_show(self) -> None:
        self._load_quick_settings()
        clf = self.app.classifier
        letters = [l for l in clf.labels if l.startswith(("letter_", "mark_"))] if clf.is_loaded else []
        if letters:
            self.info_lbl.configure(text=f"{tr('Model')}: {clf.algorithm} — {len(letters)} "
                                         f"{tr('Spelling').lower()} labels / {len(clf.labels)}")
        else:
            self.info_lbl.configure(text=tr("Spelling uses the trained ML model. Train letters first "
                                            "(Dataset → Add VSL alphabet)."))
        self._refresh_text()

    def on_frame(self, result) -> None:
        self.camera_view.show_frame(result.frame)
        for event in self.engine.update(result.predictions):
            if event.kind == "speak":
                self._speak(event.text)
            elif event.kind == "ignored" and event.message:
                self.hint_lbl.configure(text=event.message)
        st = self.engine.state()
        if st.candidate:
            self.sign_lbl.configure(text=f"{display_gesture(st.candidate)}  ({st.confidence * 100:.0f}%)")
        else:
            self.sign_lbl.configure(text="---" if not result.predictions else tr("Unknown"))
        self.hold_bar.set(1.0 if st.waiting_release else st.progress)
        if st.waiting_release:
            self.hint_lbl.configure(text=tr("Release your hand to repeat"))
        elif st.candidate:
            self.hint_lbl.configure(text=f"{tr('Hold')}… {st.progress * 100:.0f}%")
        self._refresh_text()

    def on_camera_stopped(self) -> None:
        self.camera_view.show_placeholder()
        self.sign_lbl.configure(text="---")
        self.hold_bar.set(0)


def vsl_alphabet_labels():
    """Các nhãn cần train cho chế độ đánh vần theo chuẩn NNKH (23 chữ + 2 dấu tĩnh)."""
    return [letter_label(l) for l in VSL_LETTERS] + ["mark_mu", "mark_rau"]


__all__ = ["SpellingView", "vsl_alphabet_labels", "TONE_NAMES_VI"]
