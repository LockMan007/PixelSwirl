import win32api
import win32gui
import win32con

def move_windows(source_monitor_index, destination_monitor_index):
    try:
        monitors = win32api.EnumDisplayMonitors()
        source_monitor_coords = monitors[source_monitor_index][2]
        dest_monitor_coords = monitors[destination_monitor_index][2]
        
        offset_x = dest_monitor_coords[0] - source_monitor_coords[0]
        offset_y = dest_monitor_coords[1] - source_monitor_coords[1]

        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                window_placement = win32gui.GetWindowPlacement(hwnd)
                is_maximized = window_placement[1] == win32con.SW_SHOWMAXIMIZED
                
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                
                # Check for any overlap between the window and source monitor rectangles
                overlaps_with_source = (
                    max(left, source_monitor_coords[0]) < min(right, source_monitor_coords[2]) and
                    max(top, source_monitor_coords[1]) < min(bottom, source_monitor_coords[3])
                )
                
                if overlaps_with_source:
                    # Save the restored position and size if the window is maximized
                    if is_maximized:
                        # Get the last known restored position and size
                        restored_rect = window_placement[4]
                        restored_left, restored_top, restored_right, restored_bottom = restored_rect
                        
                        # Temporarily restore the window
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        
                        # Move the restored window using its original restored position
                        win32gui.SetWindowPos(hwnd, None,
                                              restored_left + offset_x, restored_top + offset_y,
                                              restored_right - restored_left, restored_bottom - restored_top,
                                              win32con.SWP_NOZORDER)
                        
                        # Re-maximize the window
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    else:
                        # Move the non-maximized window normally
                        win32gui.SetWindowPos(hwnd, None, left + offset_x, top + offset_y,
                                              right - left, bottom - top,
                                              win32con.SWP_NOZORDER)

        win32gui.EnumWindows(callback, None)
        print(f"Moved all windows from monitor {source_monitor_index} to {destination_monitor_index}.")
        
    except IndexError:
        print("Error: Invalid monitor index provided. Please check your monitor configuration.")
    except Exception as e:
        print(f"An error occurred: {e}")

move_windows(2, 0)
input("Press Enter to exit...")
