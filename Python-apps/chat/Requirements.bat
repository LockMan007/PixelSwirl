@echo off
echo Run As Admin.
echo Installing dependencies in? %CD%\venv\
pause
python -m venv venv
call .\venv\Scripts\activate.bat
pip install pycryptodomex
pip install cryptography
pause
echo I don't think you have to install crypto, i think this was a mistake. I have spent hours working on this, and finally got it doing the most basic thing possible, so it's time for a break and then i will come back and remove this if it is not used.
echo.
echo if you still want to install this anyway, then you can press any key to continue, otherwise you can leave this window open and test it and see if it says it is missing first.
pause
echo okay, installing "crypto"
pip install crypto
echo done.
pause
