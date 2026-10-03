"""
gui/settings_view.py
====================
File này dùng để làm gì?
    Màn hình cài đặt: camera, độ phân giải, FPS, lật gương, số bàn tay,
    ngưỡng phát hiện tay, ngưỡng tin cậy, làm mượt, chế độ model, hiển thị
    landmark/bounding box, lưu lịch sử, số mẫu thu thập, theme Dark/Light,
    ngôn ngữ English/Tiếng Việt.

Dữ liệu đi vào từ đâu?
    Settings hiện tại (config/config.py) và thao tác người dùng.

Dữ liệu được xử lý như thế nào?
    Đọc giá trị các widget -> settings.update() -> settings.save() (JSON)
    -> engine.apply_settings() để áp dụng ngay (kể cả khi camera đang chạy).

Dữ liệu được truyền sang module nào?
    config/config.py, core.engine.

Kết quả trả về ở đâu?
    File config/settings.json; thay đổi có hiệu lực ngay (ngôn ngữ: sau khi khởi động lại).
"""
from __future__ import annotations

import threading
from tkinter import messagebox

import customtkinter as ctk

from camera.camera_manager import CameraManager
from config.config import FPS_OPTIONS, LANGUAGES, MODEL_MODES, RESOLUTIONS, THEMES, TTS_BACKENDS
from gui.common import BasePage, apply_treeview_style, title_label
from utils.constants import tr


class SettingsView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        title_label(self, tr("Settings")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        self.body = ctk.CTkScrollableFrame(self)
        self.body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self.body.grid_columnconfigure(1, weight=1)
        self._row = 0
        s = app.settings

        self._section("Camera")
        cam_box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.camera_combo = ctk.CTkComboBox(cam_box, values=[str(s.get("camera_index"))], width=120)
        self.camera_combo.pack(side="left")
        self.scan_btn = ctk.CTkButton(cam_box, text=tr("Scan cameras"), width=130, command=self._scan)
        self.scan_btn.pack(side="left", padx=8)
        self._add("Camera index", cam_box)
        self.res_menu = self._add("Resolution", ctk.CTkOptionMenu(self.body, values=RESOLUTIONS))
        self.fps_menu = self._add("Target FPS", ctk.CTkOptionMenu(self.body, values=FPS_OPTIONS))
        self.mirror_var = ctk.BooleanVar()
        self._add("Mirror image", ctk.CTkSwitch(self.body, text="", variable=self.mirror_var))

        self._section("Recognition")
        self.hands_seg = self._add("Number of hands", ctk.CTkSegmentedButton(self.body, values=["1", "2"]))
        self.det_slider, self.det_lbl = self._slider("Detection confidence", 0.1, 0.9, 8)
        self.conf_slider, self.conf_lbl = self._slider("Confidence threshold", 0.3, 0.95, 13)
        self.smooth_slider, self.smooth_lbl = self._slider("Smoothing window", 1, 15, 14, integer=True)
        self.mode_menu = self._add("Model mode", ctk.CTkOptionMenu(self.body, values=MODEL_MODES))
        ctk.CTkLabel(self.body, text=tr("auto: use trained ML model if available, otherwise MediaPipe built-in gestures"),
                     text_color="gray60", wraplength=600, justify="left").grid(
            row=self._next(), column=1, sticky="w", padx=10)

        self._section("Spelling")
        self.hold_s, _ = self._slider("Hold time (s)", 0.3, 2.5, 22)
        self.space_s, _ = self._slider("Auto space (s)", 0, 4, 16)
        self.tts_menu = self._add("Speech engine", ctk.CTkOptionMenu(self.body, values=TTS_BACKENDS))
        self.tts_lang_menu = self._add("Speech language", ctk.CTkOptionMenu(self.body, values=["vi", "en"]))

        self._section("Display")
        self.lm_var, self.bb_var, self.hist_var = ctk.BooleanVar(), ctk.BooleanVar(), ctk.BooleanVar()
        self._add("Show landmarks", ctk.CTkSwitch(self.body, text="", variable=self.lm_var))
        self._add("Show bounding box", ctk.CTkSwitch(self.body, text="", variable=self.bb_var))
        self._add("Save history", ctk.CTkSwitch(self.body, text="", variable=self.hist_var))
        self.samples_entry = self._add("Samples per gesture", ctk.CTkEntry(self.body, width=120))
        self.theme_menu = self._add("Theme", ctk.CTkOptionMenu(self.body, values=THEMES))
        self.lang_menu = self._add("Language", ctk.CTkOptionMenu(self.body, values=list(LANGUAGES.values())))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text=tr("Reset defaults"), fg_color="gray40", command=self._reset).pack(side="left", padx=6)
        ctk.CTkButton(btns, text=tr("Save"), width=140, command=self._save).pack(side="left", padx=6)
        self._scan_result = None
        self._load_values()

    # ------------------------------------------------------------- layout
    def _next(self) -> int:
        self._row += 1
        return self._row

    def _section(self, text: str) -> None:
        ctk.CTkLabel(self.body, text=tr(text), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=self._next(), column=0, columnspan=2, sticky="w", padx=10, pady=(16, 4))

    def _add(self, label: str, widget):
        row = self._next()
        ctk.CTkLabel(self.body, text=tr(label)).grid(row=row, column=0, sticky="w", padx=(24, 10), pady=6)
        widget.grid(row=row, column=1, sticky="w", padx=10, pady=6)
        return widget

    def _slider(self, label: str, lo: float, hi: float, steps: int, integer: bool = False):
        box = ctk.CTkFrame(self.body, fg_color="transparent")
        value_lbl = ctk.CTkLabel(box, text="", width=50)
        fmt = (lambda v: f"{int(round(v))}") if integer else (lambda v: f"{v:.2f}")
        slider = ctk.CTkSlider(box, from_=lo, to=hi, number_of_steps=steps, width=300,
                               command=lambda v: value_lbl.configure(text=fmt(v)))
        slider.pack(side="left")
        value_lbl.pack(side="left", padx=8)
        slider._fmt, slider._lbl = fmt, value_lbl
        self._add(label, box)
        return slider, value_lbl

    @staticmethod
    def _set_slider(slider, value) -> None:
        slider.set(value)
        slider._lbl.configure(text=slider._fmt(value))

    # -------------------------------------------------------------- values
    def _load_values(self) -> None:
        s = self.app.settings
        self.camera_combo.set(str(s.get("camera_index")))
        self.res_menu.set(s.get("resolution"))
        self.fps_menu.set(str(s.get("target_fps")))
        self.mirror_var.set(s.get("mirror"))
        self.hands_seg.set(str(s.get("num_hands")))
        self._set_slider(self.det_slider, s.get("min_detection_confidence"))
        self._set_slider(self.conf_slider, s.get("confidence_threshold"))
        self._set_slider(self.smooth_slider, s.get("smoothing_window"))
        self.mode_menu.set(s.get("model_mode"))
        self._set_slider(self.hold_s, s.get("spelling_hold_time"))
        self._set_slider(self.space_s, s.get("spelling_auto_space"))
        self.tts_menu.set(s.get("tts_backend"))
        self.tts_lang_menu.set(s.get("tts_lang"))
        self.lm_var.set(s.get("show_landmarks"))
        self.bb_var.set(s.get("show_bbox"))
        self.hist_var.set(s.get("save_history"))
        self.samples_entry.delete(0, "end")
        self.samples_entry.insert(0, str(s.get("collect_samples")))
        self.theme_menu.set(s.get("theme"))
        self.lang_menu.set(LANGUAGES.get(s.get("language"), "English"))

    def on_show(self) -> None:
        self._load_values()

    def _save(self) -> None:
        s = self.app.settings
        try:
            camera_index = int(self.camera_combo.get())
            samples = int(self.samples_entry.get())
            if camera_index < 0 or not 10 <= samples <= 5000:
                raise ValueError
        except ValueError:
            messagebox.showerror(tr("Error"), "Camera index must be ≥ 0 and samples between 10 and 5000.")
            return
        old_lang = s.get("language")
        lang = next((k for k, v in LANGUAGES.items() if v == self.lang_menu.get()), "en")
        s.update({
            "camera_index": camera_index,
            "resolution": self.res_menu.get(),
            "target_fps": int(self.fps_menu.get()),
            "mirror": self.mirror_var.get(),
            "num_hands": int(self.hands_seg.get() or 2),
            "min_detection_confidence": round(self.det_slider.get(), 2),
            "min_tracking_confidence": round(self.det_slider.get(), 2),
            "confidence_threshold": round(self.conf_slider.get(), 2),
            "smoothing_window": int(round(self.smooth_slider.get())),
            "model_mode": self.mode_menu.get(),
            "spelling_hold_time": round(self.hold_s.get(), 1),
            "spelling_auto_space": round(self.space_s.get(), 2),
            "tts_backend": self.tts_menu.get(),
            "tts_lang": self.tts_lang_menu.get(),
            "show_landmarks": self.lm_var.get(),
            "show_bbox": self.bb_var.get(),
            "save_history": self.hist_var.get(),
            "collect_samples": samples,
            "theme": self.theme_menu.get(),
            "language": lang,
        })
        try:
            s.save()
        except OSError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return
        ctk.set_appearance_mode(s.get("theme"))
        apply_treeview_style()
        self.app.engine.apply_settings()
        msg = tr("Settings saved")
        if lang != old_lang:
            msg += "\n" + tr("Restart the application to apply the new language.")
        messagebox.showinfo(tr("Information"), msg)

    def _reset(self) -> None:
        if messagebox.askyesno(tr("Confirm"), tr("Reset defaults") + "?"):
            self.app.settings.reset()
            self._load_values()

    # ---------------------------------------------------------------- scan
    def _scan(self) -> None:
        if self.app.engine.is_running:
            messagebox.showwarning(tr("Warning"), tr("Stop the camera before scanning."))
            return
        self.scan_btn.configure(state="disabled", text=tr("Scanning..."))
        self._scan_result = None

        def worker():
            try:
                self._scan_result = CameraManager.list_cameras()
            except Exception:
                self._scan_result = []

        threading.Thread(target=worker, daemon=True).start()
        self.after(200, self._poll_scan)

    def _poll_scan(self) -> None:
        if self._scan_result is None:
            self.after(200, self._poll_scan)
            return
        self.scan_btn.configure(state="normal", text=tr("Scan cameras"))
        cams = [str(c) for c in self._scan_result]
        if cams:
            self.camera_combo.configure(values=cams)
            self.camera_combo.set(cams[0] if self.camera_combo.get() not in cams else self.camera_combo.get())
            messagebox.showinfo(tr("Information"), f"{tr('Found cameras')}: {', '.join(cams)}")
        else:
            messagebox.showwarning(tr("Warning"), tr("No camera found"))
