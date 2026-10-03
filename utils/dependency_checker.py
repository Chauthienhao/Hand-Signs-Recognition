"""
utils/dependency_checker.py
===========================
File này dùng để làm gì?
    Kiểm tra từng thư viện cần thiết: đã cài chưa, phiên bản bao nhiêu, có
    nằm trong khoảng ĐÃ KIỂM THỬ không, import được không (bắt cả lỗi DLL),
    có xung đột gói không (opencv-python và opencv-contrib-python), và in
    hướng dẫn cài đặt/khắc phục cụ thể cho từng lỗi.

Dữ liệu đi vào từ đâu?
    - Bảng DEPENDENCIES bên dưới (khớp với requirements.txt).
    - Metadata các gói đã cài (importlib.metadata) và kết quả import thử.
    - Phiên bản Python hiện tại (utils/python_compatibility.py).

Dữ liệu được xử lý như thế nào?
    So sánh phiên bản bằng bộ phân tích phiên bản đơn giản (không cần thư
    viện ngoài). Có quy tắc riêng theo Python: Python >= 3.13 cần
    mediapipe >= 0.10.30 (các bản cũ hơn không có wheel cho 3.13+).

Dữ liệu được truyền sang module nào?
    check_environment.py (in báo cáo), main.py (quyết định có chạy hay không).

Kết quả trả về ở đâu?
    list[DependencyResult].
"""
import importlib
import re
import sys

try:
    from importlib import metadata as _metadata
except ImportError:  # pragma: no cover - Python < 3.8
    _metadata = None

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_TOO_OLD = "TOO_OLD"
STATUS_TOO_NEW = "UNVERIFIED_NEW"   # mới hơn bản đã kiểm thử -> cảnh báo
STATUS_IMPORT_ERROR = "IMPORT_ERROR"
STATUS_INCOMPATIBLE = "INCOMPATIBLE"


class Dependency(object):
    def __init__(self, name, module, dists, min_version, max_version, required=True,
                 pip_name=None, python_rules=None):
        self.name = name                    # tên hiển thị
        self.module = module                # tên dùng để import
        self.dists = dists                  # các tên gói pip có thể cung cấp module
        self.min_version = min_version      # >= (đã kiểm thử)
        self.max_version = max_version      # <  (chưa kiểm thử từ bản này)
        self.required = required
        self.pip_name = pip_name or dists[0]
        # [(python_min_tuple, min_package_version, lý do)]
        self.python_rules = python_rules or []

    def spec(self):
        return "%s>=%s,<%s" % (self.pip_name, self.min_version, self.max_version)


# Khoảng phiên bản đã kiểm thử (đồng bộ với requirements.txt)
DEPENDENCIES = [
    Dependency("OpenCV", "cv2", ["opencv-contrib-python", "opencv-python", "opencv-python-headless",
                                 "opencv-contrib-python-headless"], "4.8", "5"),
    Dependency("MediaPipe", "mediapipe", ["mediapipe"], "0.10.14", "1.1", required=False,
               python_rules=[((3, 13), "0.10.30",
                              "MediaPipe versions older than 0.10.30 have no wheels for Python 3.13+.")]),
    Dependency("NumPy", "numpy", ["numpy"], "1.24", "3"),
    Dependency("Pandas", "pandas", ["pandas"], "2.0", "4"),
    Dependency("Scikit-learn", "sklearn", ["scikit-learn"], "1.3", "2"),
    Dependency("Matplotlib", "matplotlib", ["matplotlib"], "3.10", "4"),
    Dependency("Joblib", "joblib", ["joblib"], "1.3", "2"),
    Dependency("CustomTkinter", "customtkinter", ["customtkinter"], "5.2", "7"),
    Dependency("Pillow", "PIL", ["pillow", "Pillow"], "10.1", "13"),
    # Đọc thành tiếng (chế độ Đánh vần) - tùy chọn: thiếu thì chỉ mất chức năng "Đọc"
    Dependency("pyttsx3 (TTS)", "pyttsx3", ["pyttsx3"], "2.90", "3", required=False),
    Dependency("gTTS (TTS)", "gtts", ["gTTS", "gtts"], "2.3", "3", required=False),
]


class DependencyResult(object):
    def __init__(self, dep, version, status, message="", fix=""):
        self.dep = dep
        self.version = version
        self.status = status
        self.message = message
        self.fix = fix

    @property
    def ok(self):
        return self.status in (STATUS_OK, STATUS_TOO_NEW)

    @property
    def blocking(self):
        """Lỗi khiến chương trình không thể chạy."""
        return self.dep.required and not self.ok


# ---------------------------------------------------------------- versions
def parse_version(text):
    """'2.5.3' -> (2, 5, 3); '4.14.0.94' -> (4, 14, 0, 94); '1.0.0rc1' -> (1, 0, 0)."""
    parts = []
    for piece in str(text).split("."):
        m = re.match(r"(\d+)", piece)
        if not m:
            break
        parts.append(int(m.group(1)))
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts) or (0,)


def version_lt(a, b):
    return parse_version(a) < parse_version(b)


def installed_version(dists):
    """Trả (tên gói, phiên bản) của gói đầu tiên tìm thấy, hoặc (None, None)."""
    if _metadata is None:
        return None, None
    for dist in dists:
        try:
            return dist, _metadata.version(dist)
        except Exception:
            continue
    return None, None


def installed_distributions():
    names = set()
    if _metadata is None:
        return names
    try:
        for d in _metadata.distributions():
            n = d.metadata["Name"]
            if n:
                names.add(n.lower())
    except Exception:
        pass
    return names


# ------------------------------------------------------------------ checks
def check_dependency(dep, python_version=None):
    python_version = python_version or sys.version_info[:2]
    dist, version = installed_version(dep.dists)
    install_cmd = 'python -m pip install "%s"' % dep.spec()

    if version is None:
        return DependencyResult(dep, None, STATUS_MISSING,
                                "%s is not installed." % dep.name, install_cmd)

    # Quy tắc riêng theo phiên bản Python
    for py_min, pkg_min, reason in dep.python_rules:
        if python_version >= py_min and version_lt(version, pkg_min):
            return DependencyResult(
                dep, version, STATUS_INCOMPATIBLE,
                "%s %s is not compatible with Python %d.%d. %s"
                % (dep.name, version, python_version[0], python_version[1], reason),
                'python -m pip install --upgrade "%s>=%s,<%s"' % (dep.pip_name, pkg_min, dep.max_version))

    if version_lt(version, dep.min_version):
        return DependencyResult(dep, version, STATUS_TOO_OLD,
                                "%s %s is older than the minimum tested version %s."
                                % (dep.name, version, dep.min_version),
                                'python -m pip install --upgrade "%s"' % dep.spec())

    # Import thử (phát hiện lỗi DLL / ABI dù đã cài)
    try:
        importlib.import_module(dep.module)
    except Exception as exc:
        hint = install_cmd.replace("install", "install --force-reinstall", 1)
        if dep.module in ("cv2", "mediapipe") and sys.platform.startswith("win"):
            hint += ("\n    If the error mentions a DLL, install 'Microsoft Visual C++ Redistributable "
                     "2015-2022 (x64)'.")
        return DependencyResult(dep, version, STATUS_IMPORT_ERROR,
                                "%s %s is installed but cannot be imported: %s: %s"
                                % (dep.name, version, exc.__class__.__name__, exc), hint)

    if not version_lt(version, dep.max_version):
        return DependencyResult(dep, version, STATUS_TOO_NEW,
                                "%s %s is newer than the tested range (<%s); it may work but is not verified."
                                % (dep.name, version, dep.max_version),
                                'python -m pip install "%s"   (to use a verified version)' % dep.spec())
    return DependencyResult(dep, version, STATUS_OK, "")


def check_mediapipe_tasks_api():
    """Kiểm tra API MediaPipe Tasks mà dự án dùng có tồn tại không. Trả (ok, message)."""
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        _ = (mp.Image, mp.ImageFormat.SRGB, mp_python.BaseOptions,
             vision.GestureRecognizer, vision.GestureRecognizerOptions, vision.RunningMode.VIDEO)
        return True, "MediaPipe Tasks API available"
    except Exception as exc:
        return False, "MediaPipe Tasks API not available: %s: %s" % (exc.__class__.__name__, exc)


def find_conflicts():
    """Phát hiện các gói cùng cung cấp module cv2 -> ghi đè lẫn nhau."""
    names = installed_distributions()
    cv_pkgs = sorted(n for n in names if n.startswith("opencv-"))
    conflicts = []
    if len(cv_pkgs) > 1:
        extra = [n for n in cv_pkgs if n != "opencv-contrib-python"]
        conflicts.append((
            "Several OpenCV packages are installed (%s); they overwrite each other's cv2 module."
            % ", ".join(cv_pkgs),
            "python -m pip uninstall -y %s\n    python -m pip install --force-reinstall "
            "\"opencv-contrib-python>=4.8,<5\"" % " ".join(extra)))
    return conflicts


def check_all():
    return [check_dependency(dep) for dep in DEPENDENCIES]
