"""
utils/python_compatibility.py
=============================
File này dùng để làm gì?
    Kiểm tra phiên bản Python đang chạy có nằm trong danh sách ĐÃ KIỂM THỬ
    hay không, kiểm tra kiến trúc 64-bit, đưa ra phiên bản Python khuyến
    nghị và hướng dẫn tạo virtual environment bằng `py -3.x`.
    Đồng thời chứa các bản vá tương thích nhỏ (runtime patches) cho những
    lỗi đã phát hiện khi kiểm thử.

Dữ liệu đi vào từ đâu?
    sys.version_info, platform, struct (thông tin trình thông dịch hiện tại).

Dữ liệu được xử lý như thế nào?
    So sánh phiên bản với bảng PYTHON_SUPPORT. Bảng này được lập từ kết quả
    kiểm thử thực tế (xem README mục "Bảng tương thích"), KHÔNG phải đoán.
    Phiên bản Python chưa có trong bảng -> trạng thái "Not verified"
    (cảnh báo, không chặn); thấp hơn MIN_PYTHON -> "Not supported" (chặn).

Dữ liệu được truyền sang module nào?
    check_environment.py, utils/dependency_checker.py, main.py.

Kết quả trả về ở đâu?
    Đối tượng PythonCheck; hoặc in ra màn hình khi chạy trực tiếp:
        python utils/python_compatibility.py   (mã thoát 0 = dùng được)

LƯU Ý: file này cố ý chỉ dùng thư viện chuẩn và cú pháp đơn giản để vẫn chạy
được (và báo lỗi rõ ràng) trên cả các bản Python cũ.
"""
import platform
import struct
import sys

# Phiên bản thấp nhất được hỗ trợ (3.9 đã hết vòng đời 10/2025, không kiểm thử)
MIN_PYTHON = (3, 10)
RECOMMENDED_PYTHON = "3.12"

# Kết quả kiểm thử thực tế: (trạng thái, ghi chú)
#   Supported      : đã cài + chạy toàn bộ bộ test (dữ liệu, training, MediaPipe thật, GUI)
#   Not supported  : thấp hơn MIN_PYTHON
PYTHON_SUPPORT = {
    (3, 10): ("Supported", "Tested. Oldest supported version."),
    (3, 11): ("Supported", "Tested. Recommended."),
    (3, 12): ("Supported", "Tested. Recommended."),
    (3, 13): ("Supported", "Tested. Requires mediapipe>=0.10.30."),
    (3, 14): ("Supported", "Tested. Requires mediapipe>=0.10.30."),
}
LATEST_VERIFIED = max(PYTHON_SUPPORT)

STATUS_SUPPORTED = "Supported"
STATUS_UNVERIFIED = "Not verified"
STATUS_UNSUPPORTED = "Not supported"


class PythonCheck(object):
    def __init__(self, version, status, note, is_64bit, ok):
        self.version = version          # "3.12.7"
        self.status = status            # Supported / Not verified / Not supported
        self.note = note
        self.is_64bit = is_64bit
        self.ok = ok                    # False -> không nên chạy chương trình

    def __repr__(self):
        return "PythonCheck(%s, %s)" % (self.version, self.status)


def python_version_str():
    return "%d.%d.%d" % sys.version_info[:3]


def architecture():
    bits = struct.calcsize("P") * 8
    machine = platform.machine() or "unknown"
    return bits, machine


def check_python():
    major_minor = sys.version_info[:2]
    bits, _machine = architecture()
    is_64 = bits == 64
    if major_minor < MIN_PYTHON:
        status, note = STATUS_UNSUPPORTED, (
            "Python %d.%d is older than the minimum supported version %d.%d."
            % (major_minor[0], major_minor[1], MIN_PYTHON[0], MIN_PYTHON[1]))
    elif major_minor in PYTHON_SUPPORT:
        status, note = PYTHON_SUPPORT[major_minor]
    else:
        status, note = STATUS_UNVERIFIED, (
            "Python %d.%d is newer than the latest verified version %d.%d. "
            "It may work if all dependencies install correctly, but it has not been tested."
            % (major_minor[0], major_minor[1], LATEST_VERIFIED[0], LATEST_VERIFIED[1]))
    if not is_64:
        note += " 32-bit Python is not supported by MediaPipe; install 64-bit Python."
    ok = status != STATUS_UNSUPPORTED and is_64
    return PythonCheck(python_version_str(), status, note, is_64, ok)


def venv_instructions(version=RECOMMENDED_PYTHON):
    return (
        "Create a separate virtual environment with a supported Python version\n"
        "(this does NOT change or remove your current Python):\n"
        "    py --list                     (show installed Python versions)\n"
        "    py -{v} -m venv .venv\n"
        "    .venv\\Scripts\\activate\n"
        "    python -m pip install --upgrade pip\n"
        "    pip install -r requirements.txt\n"
        "If Python {v} is not installed, download the 64-bit installer from\n"
        "    https://www.python.org/downloads/windows/"
    ).format(v=version)


# ---------------------------------------------------------------------------
# Bản vá tương thích (chỉ áp dụng đúng trường hợp đã phát hiện khi kiểm thử)
# ---------------------------------------------------------------------------
def apply_runtime_patches():
    """Gọi 1 lần khi khởi động, trước khi tạo giao diện.

    Vá 1 - tkinter (Python < 3.11) + Tcl/Tk 9:
        Tk 9 trả về chuỗi rỗng "" thay vì "none" cho menu rỗng, khiến
        Menu.index()/Menu.delete() của Python 3.10 ném TclError
        ("expected integer but got ''") khi CustomTkinter tạo ComboBox/OptionMenu.
        Python 3.11+ đã sửa; bản vá dưới đây đưa đúng hành vi của 3.11 về 3.10.
    """
    applied = []
    if sys.version_info < (3, 11):
        try:
            import tkinter

            if not getattr(tkinter.Menu, "_hsr_patched", False):
                def index(self, index):
                    i = self.tk.call(self._w, "index", index)
                    return None if i in ("", "none") else self.tk.getint(i)

                def delete(self, index1, index2=None):
                    if index2 is None:
                        index2 = index1
                    num1, num2 = self.index(index1), self.index(index2)
                    if num1 is None or num2 is None:
                        num1, num2 = 0, -1
                    for i in range(num1, num2 + 1):
                        if "command" in self.entryconfig(i):
                            c = str(self.entrycget(i, "command"))
                            if c:
                                self.deletecommand(c)
                    self.tk.call(self._w, "delete", index1, index2)

                tkinter.Menu.index = index
                tkinter.Menu.delete = delete
                tkinter.Menu._hsr_patched = True
                applied.append("tkinter.Menu (Tk 9 on Python 3.10)")
        except Exception:
            pass
    return applied


def main():
    res = check_python()
    bits, machine = architecture()
    print("Python version : %s" % res.version)
    print("Architecture   : %d-bit (%s)" % (bits, machine))
    print("Status         : %s" % res.status)
    print("Note           : %s" % res.note)
    if not res.ok:
        print("")
        print(venv_instructions())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
