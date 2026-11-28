@echo off
setlocal
cd /d "%~dp0"

if not defined GEMINI_API_KEY (
  set /p "GEMINI_API_KEY=請貼上 Gemini API 金鑰（輸入後不會保存到檔案）："
)

if not defined GEMINI_API_KEY (
  echo [錯誤] 尚未提供 GEMINI_API_KEY。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo 正在建立虛擬環境...
  where py >nul 2>nul
  if %errorlevel% equ 0 (
    py -m venv .venv
  ) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
      python -m venv .venv
    ) else (
      echo [錯誤] 找不到 Python。請先安裝 Python，並勾選 "Add python.exe to PATH"。
      pause
      exit /b 1
    )
  )
  if %errorlevel% neq 0 (
    echo [錯誤] 無法建立虛擬環境。
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -c "import streamlit, google.genai" >nul 2>nul
if %errorlevel% neq 0 (
  echo 正在安裝所需套件...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if %errorlevel% neq 0 (
    echo [錯誤] 套件安裝失敗。
    pause
    exit /b 1
  )
)

echo 正在啓動宿舍食譜助手，瀏覽器將會自動開啓。
".venv\Scripts\python.exe" -m streamlit run app.py ^
  --server.headless=true ^
  --server.port=8501 ^
  --browser.gatherUsageStats=false

if %errorlevel% neq 0 (
  echo [錯誤] App 啓動失敗。
  pause
)

endlocal
