@echo off
setlocal
cd /d "%~dp0"
set /p URL=Nhap URL catalog (https://.../orbis/catalog.json): 
if "%URL%"=="" exit /b 1
py -3 prepare_native.py --catalog-url "%URL%" --out ChepGameStore-PS4
if errorlevel 1 (
  echo Loi tao source. Can Python 3 va Git, hoac build qua GitHub Actions.
) else (
  echo Da tao thu muc source ChepGameStore-PS4.
  echo De tao file PKG phai co OpenOrbis SDK, nen dung GitHub Actions.
)
pause
