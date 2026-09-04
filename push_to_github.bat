@echo off
chcp 65001 >nul
title Push First Principles Web to GitHub
color 0A

setlocal EnableDelayedExpansion

:: ============================================================
:: Cau hinh
:: ============================================================
set "LOCAL_DIR=D:\Quant_ckvn\hub\first_principles_web"
set "REMOTE_URL=https://github.com/phat2814backup-quant/first_principles_web.git"
set "BRANCH=main"

:: ============================================================
echo.
echo  ========================================================
echo   AUTO PUSH - first_principles_web
echo  ========================================================
echo.
echo  Thu muc local : %LOCAL_DIR%
echo  Remote        : %REMOTE_URL%
echo  Branch        : %BRANCH%
echo.

:: Kiem tra thu muc ton tai
if not exist "%LOCAL_DIR%" (
    echo  [LOI] Khong tim thay thu muc:
    echo         %LOCAL_DIR%
    echo.
    echo  Hay tao thu muc hoac sua duong dan trong file .bat nay.
    pause
    exit /b 1
)

cd /d "%LOCAL_DIR%"
if errorlevel 1 (
    echo  [LOI] Khong the vao thu muc %LOCAL_DIR%
    pause
    exit /b 1
)

:: Kiem tra git co cai khong
where git >nul 2>&1
if errorlevel 1 (
    echo  [LOI] Chua cai Git hoac Git khong co trong PATH.
    echo  Tai tai: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Neu chua phai git repo -> init + remote
if not exist "%LOCAL_DIR%\.git" (
    echo  [INFO] Chua co .git - dang khoi tao repository...
    git init
    git branch -M %BRANCH%
    git remote add origin %REMOTE_URL% 2>nul
    if errorlevel 1 (
        git remote set-url origin %REMOTE_URL%
    )
    echo  [OK] Da init va gan remote origin.
    echo.
)

:: Dam bao remote dung
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin %REMOTE_URL%
) else (
    git remote set-url origin %REMOTE_URL%
)

echo  [1/4] Dang kiem tra trang thai...
git status --short
echo.

:: Tao commit message mac dinh
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "TODAY=%%c-%%b-%%a"
for /f "tokens=1-2 delims=: " %%a in ("%time%") do set "NOW=%%a%%b"
set "DEFAULT_MSG=update %TODAY% %time:~0,5%"

echo  [2/4] Commit message
set "COMMIT_MSG="
set /p "COMMIT_MSG=  Nhap noi dung commit [Enter = dung mac dinh]: "
if "!COMMIT_MSG!"=="" set "COMMIT_MSG=%DEFAULT_MSG%"

echo.
echo  [3/4] git add -A ...
git add -A
if errorlevel 1 (
    echo  [LOI] git add that bai.
    pause
    exit /b 1
)

:: Kiem tra co thay doi de commit khong
git diff --cached --quiet
if errorlevel 1 (
    echo  [OK] Co thay doi - dang commit...
    git commit -m "!COMMIT_MSG!"
    if errorlevel 1 (
        echo  [LOI] Commit that bai.
        pause
        exit /b 1
    )
) else (
    echo  [INFO] Khong co thay doi moi de commit.
    echo  Van tiep tuc push [neu remote chua dong bo]...
)

echo.
echo  [4/4] Dang push len GitHub (%BRANCH%)...
git push -u origin %BRANCH%
if errorlevel 1 (
    echo.
    echo  [LOI] Push that bai.
    echo  Nguyen nhan thuong gap:
    echo    - Chua dang nhap GitHub [Personal Access Token / SSH]
    echo    - Branch remote khac ten [master vs main]
    echo    - Can pull truoc: git pull origin %BRANCH% --rebase
    echo.
    echo  Thu chay thu cong:
    echo    cd /d "%LOCAL_DIR%"
    echo    git pull origin %BRANCH% --rebase
    echo    git push -u origin %BRANCH%
    echo.
    pause
    exit /b 1
)

echo.
echo  ========================================================
echo   THANH CONG - Da push len GitHub
echo   https://github.com/phat2814backup-quant/first_principles_web
echo  ========================================================
echo.
pause
endlocal
