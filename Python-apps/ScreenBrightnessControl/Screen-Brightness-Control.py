# pip install screen-brightness-control keyboard pystray Pillow
# or:
# pip install screen-brightness-control 
# pip install keyboard 
# pip install pystray 
# pip install Pillow

# Coded with Gemini 3 Pro 11/27/2025

import screen_brightness_control as sbc
import keyboard
import pystray
from PIL import Image, ImageDraw
import tkinter as tk
import threading
import time
import queue

# --- CONFIGURATION ---
STEP = 5                   # Changed to 5% as requested
OSD_DURATION_MS = 1500     
FONT_SIZE = 30             
TEXT_COLOR = "#FF01FF"     # Fushia Text
BG_COLOR = "#424242"       # near Black Background for high contrast

# --- GLOBAL STATE ---
# We store the brightness locally so we don't have to query the monitor constantly
target_brightness = 50 
running = True

# A queue to handle hardware updates without freezing the screen
brightness_queue = queue.Queue()
def get_initial_brightness():
    """Gets real brightness once at startup."""
    try:
        val = sbc.get_brightness()
        if isinstance(val, list):
            return val[0]
        return val
    except:
        return 50

# Initialize
target_brightness = get_initial_brightness()

# --- HARDWARE WORKER THREAD ---
def hardware_updater_loop():
    """
    This runs in the background. It takes the latest brightness 
    setting and applies it to the monitor so the UI doesn't freeze.
    """
    global running
    last_applied = -1
    while running:
        try:
            # Check if there is a new brightness target
            # We use a non-blocking check or a short timeout
            current_target = brightness_queue.get(timeout=0.1)

            # Clear out any older queued items (debounce), we only want the latest
            while not brightness_queue.empty():
                try:
                    current_target = brightness_queue.get_nowait()
                except queue.Empty:
                    break

            # Only talk to hardware if the value actually changed
            if current_target != last_applied:
                sbc.set_brightness(current_target)
                last_applied = current_target
            brightness_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Hardware Error: {e}")

# --- INPUT HANDLING ---
def change_target_brightness(amount):
    global target_brightness

    # Update the variable INSTANTLY
    target_brightness = max(0, min(100, target_brightness + amount))

    # 1. Update the UI immediately (Visual)
    update_osd_text(target_brightness)

    # 2. Tell the background worker to handle the hardware (Hardware)
    brightness_queue.put(target_brightness)

# --- GUI / OSD SECTION ---
root = tk.Tk()
root.overrideredirect(True)
root.wm_attributes("-topmost", True)
root.wm_attributes("-disabled", True)
root.wm_attributes("-transparentcolor", "magenta") # Magenta will be invisible
root.config(bg="magenta") # The whole window is invisible...

# ...Except this frame, which is BLACK
frame = tk.Frame(root, bg=BG_COLOR, padx=5, pady=1)
frame.pack()

# The Text Label
label = tk.Label(frame, text="", font=("Consolas", FONT_SIZE, "bold"), fg=TEXT_COLOR, bg=BG_COLOR)
label.pack()

# Positioning
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
w = 450
h = 120
x = (screen_width // 2) - (w // 2)
y = (screen_height // 2) - (h // 2)
root.geometry(f"{w}x{h}+{x}+{y}")
root.withdraw()
osd_hide_timer = None

def hide_osd():
    root.withdraw()

def update_osd_text(val):
    global osd_hide_timer

    # Update text
    label.config(text=f"Brightness: {val}%")

    # Show window
    root.deiconify()

    # Reset Timer
    if osd_hide_timer:
        root.after_cancel(osd_hide_timer)
    osd_hide_timer = root.after(OSD_DURATION_MS, hide_osd)

# --- SYSTEM TRAY ---
def create_icon():
    image = Image.new('RGB', (64, 64), color=(50, 50, 50))
    d = ImageDraw.Draw(image)
    d.ellipse((15, 15, 49, 49), fill="yellow")
    return image

def quit_app(icon, item):
    global running
    running = False
    icon.stop()
    root.quit()

def run_tray():
    icon = pystray.Icon("Brightness", create_icon(), "Brightness Control", 
                        menu=pystray.Menu(pystray.MenuItem("Exit", quit_app)))
    icon.run()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Start Hardware Worker Thread
    t_hw = threading.Thread(target=hardware_updater_loop, daemon=True)
    t_hw.start()

    # Start Tray Thread
    t_tray = threading.Thread(target=run_tray, daemon=True)
    t_tray.start()

    # Hotkeys (Now calling the instant function)
    keyboard.add_hotkey('alt+page up', lambda: change_target_brightness(STEP))
    keyboard.add_hotkey('alt+page down', lambda: change_target_brightness(-STEP))

    # Start UI
    root.mainloop()
