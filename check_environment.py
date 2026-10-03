"""
check_environment.py
====================
File này dùng để làm gì?
    Kiểm tra toàn bộ môi trường trước khi chạy chương trình:
    phiên bản Python, hệ điều hành, kiến trúc, các thư viện (đã cài, phiên bản,
    tương thích, import được), MediaPipe Tasks API và xung đột gói.

Dữ liệu đi vào từ đâu?
    utils/python_compatibility.py và utils/dependency_checker.py.

Dữ liệu được xử lý như thế nào?
    Tổng hợp kết quả thành báo cáo [✓]/[!]/[✗] kèm lý do và lệnh khắc phục.

Dữ liệu được truyền sang module nào?
    Không truyền; in ra màn hình.

Kết quả trả về ở đâu?
    Console. Mã thoát: 0 = READY, 1 = chưa sẵn sàng.

Chạy:
    python check_environment.py
"""
import os
import platform
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Console Windows cũ (cp1252) không in được ký tự ✓ ✗ -> chuyển sang UTF-8 nếu được
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from utils import python_compatibility as pc  # noqa: E402

OK, WARN, FAIL = "[✓]", "[!]", "[✗]"


def run():
    lines = []
    out = lines.append
    py = pc.check_python()
    bits, machine = pc.architecture()

    out("-" * 60)
    out("HAND SIGN RECOGNITION")
    out("ENVIRONMENT CHECK")
    out("-" * 60)
    out("Python version   : %s" % py.version)
    out("Python path      : %s" % sys.executable)
    out("Operating System : %s %s" % (platform.system(), platform.release()))
    out("Architecture     : %s (%d-bit)" % (machine, bits))
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    out("Virtual env      : %s" % ("yes (%s)" % sys.prefix if in_venv else "NO - using system Python"))
    out("")

    problems, warnings, fixes = [], [], []
    if py.status == pc.STATUS_SUPPORTED and py.ok:
        out("%s Python %s  (%s)" % (OK, py.version, py.note))
    elif py.ok:
        out("%s Python %s" % (WARN, py.version))
        out("    Reason: %s" % py.note)
        out("    Recommended Python version: %s" % pc.RECOMMENDED_PYTHON)
        warnings.append("Python version not verified")
    else:
        out("%s Python %s" % (FAIL, py.version))
        out("    Reason: %s" % py.note)
        out("    Recommended Python version: %s" % pc.RECOMMENDED_PYTHON)
        problems.append("Python")
        fixes.append(pc.venv_instructions())

    if not in_venv:
        warnings.append("not in a virtual environment")

    # Các thư viện (chỉ kiểm tra khi Python đủ mới để import được module)
    if sys.version_info[:2] >= (3, 7):
        from utils import dependency_checker as dc
        for res in dc.check_all():
            name = res.dep.name
            if res.status == dc.STATUS_OK:
                out("%s %-14s %s" % (OK, name, res.version))
                continue
            symbol = WARN if (res.ok or not res.dep.required) else FAIL
            out("%s %-14s %s" % (symbol, name, res.version or "not installed"))
            out("    Reason: %s" % res.message)
            if res.status == dc.STATUS_INCOMPATIBLE or (res.status == dc.STATUS_MISSING and name == "MediaPipe"
                                                       and sys.version_info[:2] > pc.LATEST_VERIFIED):
                out("    Recommended Python version: %s" % pc.RECOMMENDED_PYTHON)
            if res.fix:
                out("    Fix: %s" % res.fix)
            if res.blocking:
                problems.append(name)
            elif not res.ok:
                if name == "MediaPipe":
                    warnings.append("MediaPipe unavailable -> camera/recognition disabled")
                elif "TTS" in name:
                    warnings.append(name + " unavailable -> 'Speak' may not work")
                else:
                    warnings.append(name)
            else:
                warnings.append("%s version not verified" % name)

        mp_res = [r for r in dc.check_all() if r.dep.module == "mediapipe"][0]  # noqa: E501
        if mp_res.ok:
            api_ok, msg = dc.check_mediapipe_tasks_api()
            out("%s %-14s %s" % (OK if api_ok else FAIL, "MediaPipe API", msg))
            if not api_ok:
                problems.append("MediaPipe Tasks API")
                fixes.append('python -m pip install --upgrade "mediapipe>=0.10.14,<1.1"')

        try:
            import tkinter
            out("%s %-14s Tk %s" % (OK, "Tkinter", tkinter.TkVersion))
        except Exception as exc:
            out("%s %-14s %s" % (FAIL, "Tkinter", exc))
            out("    Fix: reinstall Python and tick 'tcl/tk and IDLE'.")
            problems.append("Tkinter")

        for message, fix in dc.find_conflicts():
            out("%s Conflict: %s" % (WARN, message))
            out("    Fix: %s" % fix)
            warnings.append("package conflict")

    out("")
    if problems:
        out("Environment Status: NOT READY  (problems: %s)" % ", ".join(problems))
        for f in fixes:
            out("")
            out(f)
        if "Python" not in problems:
            out("")
            out("Install / repair all dependencies inside your virtual environment:")
            out("    python -m pip install -r requirements.txt")
    elif warnings:
        out("Environment Status: READY WITH WARNINGS  (%s)" % "; ".join(warnings))
    else:
        out("Environment Status: READY")
    out("-" * 60)
    return (1 if problems else 0), lines


def main():
    code, lines = run()
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
