@echo off
echo Run As Admin.
echo Installing dependencies in? %CD%\venv\
pause
python -m venv venv
call .\venv\Scripts\activate.bat
pip install pycryptodomex
pip install cryptography
pip install crypto
pause