# Requirement:
# pip install pywin32

import win32api
import win32gui
import win32con

def move_windows(source_monitor_index, destination_monitor_index):
    """
    Moves all windows from a source monitor to a destination monitor.
    
    Args:
        source_monitor_index (int): The index of the monitor to move windows from.
        destination_monitor_index (int): The index of the monitor to move windows to.
    """
    try:
        # Get information about all monitors
        monitors = win32api.EnumDisplayMonitors()
        source_monitor_coords = monitors[source_monitor_index][2]
        dest_monitor_coords = monitors[destination_monitor_index][2]
        
        # Calculate the offset to move windows by
        offset_x = dest_monitor_coords[0] - source_monitor_coords[0]
        offset_y = dest_monitor_coords[1] - source_monitor_coords[1]

        def callback(hwnd, extra):
            # Check if the window is visible
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                # Get the window's position and dimensions
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                
                # Check if the window is on the source monitor
                if source_monitor_coords[0] <= left < source_monitor_coords[2] and \
                   source_monitor_coords[1] <= top < source_monitor_coords[2]:
                    # Move the window
                    win32gui.SetWindowPos(hwnd, None, left + offset_x, top + offset_y,
                                          right - left, bottom - top,
                                          win32con.SWP_NOZORDER)

        win32gui.EnumWindows(callback, None)
        print(f"Moved all windows from monitor {source_monitor_index} to {destination_monitor_index}.")
        
    except IndexError:
        print("Error: Invalid monitor index provided. Please check your monitor configuration.")

# Assuming your monitors are indexed from 0 (Left, Middle, Right) and you want to move Right to Middle.
move_windows(2, 0)

# Add this line at the end to pause the script
input("Press Enter to exit...")