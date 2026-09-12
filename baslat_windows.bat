@echo off
REM ============================================================================
REM  ReLoop - Windows BASLATICI  (CIFT TIKLA calisir; komut yazmak YOK)
REM  Python bulur -> sanal ortam kurar -> bagimliliklari yukler ->
REM  backend'i baslatir -> tarayicida arayuzu acar.
REM  Adres: http://127.0.0.1:8000/app   Kapatmak icin bu pencereyi kapatin.
REM ============================================================================
setlocal
cd /d "%~dp0"
echo ReLoop klasoru: %CD%

REM --- Python var mi? ---
where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (
  where python >nul 2>&1
  if %errorlevel%==0 (set PY=python) else (
    echo.
    echo   HATA: Python bulunamadi.
    echo   Kur:  https://www.python.org/downloads/   ^(kurulumda "Add to PATH" isaretleyin^)
    echo.
    pause
    exit /b 1
  )
)
%PY% --version

cd backend

REM --- Sanal ortam (ilk acilista bir kez) ---
if not exist ".venv" (
  echo.
  echo ^>^> Ilk kurulum: sanal ortam olusturuluyor ^(bir kez^)...
  %PY% -m venv .venv
)

set VENV_PY=.venv\Scripts\python.exe

REM --- Bagimliliklar ---
"%VENV_PY%" -c "import fastapi, uvicorn, sqlalchemy, reportlab, qrcode, numpy" >nul 2>&1
if not %errorlevel%==0 (
  echo ^>^> Bagimliliklar yukleniyor ^(bir kez^)...
  "%VENV_PY%" -m pip install --upgrade pip >nul 2>&1
  "%VENV_PY%" -m pip install -r requirements.txt
  if not %errorlevel%==0 (
    echo.
    echo   Bagimliliklar yuklenemedi ^(internet baglantisini kontrol edin^).
    pause
    exit /b 1
  )
)

echo.
echo ^>^> Backend baslatiliyor...
echo ^>^> Arayuz:  http://127.0.0.1:8000/app
echo ^>^> Swagger: http://127.0.0.1:8000/docs
echo.

REM Tarayiciyi birkac saniye sonra ac
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/app"

REM Backend'i baslat (bu pencerede calisir; kapatmak icin pencereyi kapatin)
"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
