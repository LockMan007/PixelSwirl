.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build  --use-sage-attention --reserve-vram 4
echo If you see this and ComfyUI did not start try updating your Nvidia Drivers to the latest.
pause
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --disable-cuda-malloc --disable-auto-launch