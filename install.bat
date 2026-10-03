@echo off
chcp 65001 >nul
setlocal
REM ==========================================================================
REM  Hand Signs Recognition System - cai dat tu dong tren Windows
REM
REM  Cach dung:
REM     install.bat            dung lenh "python" mac dinh tren may
REM     install.bat 3.12       dung Python 3.12 qua Python Launcher (py -3.12)
REM
REM  Script chi tao moi truong ao .venv TRONG thu muc project. Khong cai dat,
REM  go bo hay thay doi Python he thong, PATH hay goi cua nguoi dung.
REM ==========================================================================
cd /d "%~dp0"

if "%~1"=="" (
    set "PYCMD=python"
) else (
    set "PYCMD=py -%~1"
)

echo === Python duoc chon: %PYCMD%
%PYCMD% --version
if errorlevel 1 (
    echo [LOI] Khong chay duoc "%PYCMD%".
    echo Cac phien ban Python dang co tren may:
    py --list 2>nul
    echo Cai Python 64-bit tai https://www.python.org/downloads/windows/
    goto :fail
)

echo.
echo === Kiem tra phien ban Python
%PYCMD% utils\python_compatibility.py
if errorlevel 1 (
    echo.
    echo Cac phien ban Python dang co tren may:
    py --list 2>nul
    echo Vi du chay lai voi Python 3.12:   install.bat 3.12
    goto :fail
)

if exist ".venv\Scripts\python.exe" (
    echo.
    echo === Da co moi truong .venv - su dung lai:
    .venv\Scripts\python.exe --version
    echo     ^(Muon doi phien ban Python: xoa thu muc .venv roi chay lai install.bat^)
) else (
    echo.
    echo === Tao moi truong ao .venv
    %PYCMD% -m venv .venv
    if errorlevel 1 goto :fail
)

set "VPY=.venv\Scripts\python.exe"
echo.
echo === Nang cap pip
%VPY% -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo.
echo === Cai thu vien da kiem thu (requirements-lock.txt) - co the mat 5-10 phut
echo     KHONG dong cua so va KHONG bam phim trong luc cai.
%VPY% -m pip install -r requirements-lock.txt
if errorlevel 1 (
    echo.
    echo [CANH BAO] Cai bang lock file that bai, thu lai voi requirements.txt ...
    %VPY% -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
)

echo.
%VPY% check_environment.py
if errorlevel 1 goto :fail
echo.
echo HOAN TAT. Chay chuong trinh:
echo     PowerShell :  .\run.bat
echo     CMD        :  run.bat
echo     Hoac double-click file run.bat trong File Explorer
pause
exit /b 0

:fail
echo.
echo [LOI] Cai dat chua thanh cong. Doc thong bao phia tren hoac xem README.md muc 14.
pause
exit /b 1
