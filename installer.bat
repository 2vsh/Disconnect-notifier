@echo off

echo Installing required Python packages...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo There was an error installing the packages. Please check the error messages above.
    pause
    exit /b %errorlevel%
)

echo Installation complete.
echo Success. You now need to install Tesseract for OCR. Prompting download now...

:: Wait for approximately 6 seconds
ping 127.0.0.1 -n 7 >nul

start https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.4.20240503.exe

echo Download the Tesseract installer from the prompted link.
