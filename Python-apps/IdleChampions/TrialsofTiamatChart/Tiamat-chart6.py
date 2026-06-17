import re, json, os, tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Tier to Health Mapping
TIER_DATA = {
    1: {"name": "Normal", "health": 4.00e08}, 2: {"name": "Heroic", "health": 7.50e08},
    3: {"name": "Veteran", "health": 1.30e09}, 4: {"name": "Master", "health": 2.00e09},
    5: {"name": "Epic", "health": 2.90e09}, 6: {"name": "Mythic", "health": 4.30e09},
    7: {"name": "Grand Legend", "health": 6.10e09}, 8: {"name": "Grand Torment", "health": 8.60e09},
    9: {"name": "Master of Torment", "health": 12.00e09}, 10: {"name": "Tiamat Reborn", "health": 16.00e09}
}

SETTINGS_FILE = "settings.json"
PLOT_FILE = "plot_data.json"
history = [] 
tracking_id = None
start_time = None
total_seconds_at_start = 0
initial_hp_at_start = 0

def reload_chart():
    global history
    if os.path.exists(PLOT_FILE):
        try:
            with open(PLOT_FILE, "r") as f:
                history = json.load(f)
                update_chart()
                messagebox.showinfo("Success", "Chart reloaded successfully from plot_data.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse plot_data.json.\n{e}")
    else:
        messagebox.showwarning("Warning", "plot_data.json not found.")

def strip_non_numeric(val): return re.sub(r'\D', '', val)

def format_time_delta(seconds):
    delta = timedelta(seconds=int(max(0, seconds)))
    return f"{delta.days}d {delta.seconds // 3600}h {(delta.seconds // 60) % 60}m"

def save_all():
    data = {
        "tier": tier_entry.get(), "dps": dps_entry.get(), 
        "hp_main": health_entry.get(), "hp_sub": health_suffix_entry.get(), 
        "d": days_entry.get(), "h": hours_entry.get(), "m": mins_entry.get(),
        "start_time": start_time.isoformat() if start_time else None,
        "total_seconds_at_start": total_seconds_at_start,
        "initial_hp_at_start": initial_hp_at_start
    }
    with open(SETTINGS_FILE, "w") as f: json.dump(data, f)
    with open(PLOT_FILE, "w") as f: json.dump(history, f)

def load_all():
    global history, start_time, total_seconds_at_start, initial_hp_at_start
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                data = json.load(f)
                tier_entry.delete(0, tk.END); tier_entry.insert(0, data.get("tier", "9"))
                dps_entry.delete(0, tk.END); dps_entry.insert(0, data.get("dps", "35160"))
                health_entry.delete(0, tk.END); health_entry.insert(0, data.get("hp_main", "3483"))
                health_suffix_entry.delete(0, tk.END); health_suffix_entry.insert(0, data.get("hp_sub", "000000"))
                days_entry.delete(0, tk.END); days_entry.insert(0, data.get("d", "3"))
                hours_entry.delete(0, tk.END); hours_entry.insert(0, data.get("h", "4"))
                mins_entry.delete(0, tk.END); mins_entry.insert(0, data.get("m", "46"))
                
                saved_start = data.get("start_time")
                if saved_start:
                    start_time = datetime.fromisoformat(saved_start)
                    total_seconds_at_start = data.get("total_seconds_at_start", 0)
                    initial_hp_at_start = data.get("initial_hp_at_start", 0)
            except: pass 
    
    if os.path.exists(PLOT_FILE):
        with open(PLOT_FILE, "r") as f:
            try:
                history = json.load(f)
                update_chart()
            except: history = []
    else:
        history = []
        
    if start_time:
        run_update()

def update_chart():
    ax.clear()
    
    # Configure axes
    ax.yaxis.tick_right()
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])
    
    if history:
        # 1. Draw the main progress line (Green)
        x_vals = [p[0] for p in history]
        y_vals = [p[1] for p in history]
        ax.plot(x_vals, y_vals, 'g-o')
        
        try:
            tier_val = int(strip_non_numeric(tier_entry.get()))
            current_live_dps = float(strip_non_numeric(dps_entry.get()))
            total_hp = TIER_DATA[tier_val]["health"]
            
            # 2. Draw historical points' projections (lighter, dotted) for ALL points
            for i in range(len(history)):
                pt_x = history[i][0]
                pt_y = history[i][1]
                
                # Retrieve the historical snapshot DPS if it exists, otherwise fallback safely
                if len(history[i]) > 2:
                    pt_dps = float(history[i][2])
                else:
                    pt_dps = current_live_dps
                
                if pt_dps > 0 and pt_y > 0:
                    # Calculate remaining HP based exactly on this standalone point's percentage
                    remaining_hp_at_point = (pt_y / 100.0) * total_hp
                    # Determine independent time length to hit zero based purely on its unique DPS
                    hours_to_kill = (remaining_hp_at_point / pt_dps) / 3600.0
                    proj_x = pt_x + hours_to_kill
                    
                    ax.plot([pt_x, proj_x], [pt_y, 0], 'r:', linewidth=1, alpha=0.5)

            # 3. Draw the latest point's projection using live DPS (darker, dashed)
            if len(history) > 0:
                last_x = history[-1][0]
                last_y = history[-1][1]
                if current_live_dps > 0 and last_y > 0:
                    remaining_hp = (last_y / 100.0) * total_hp
                    hours_to_kill = (remaining_hp / current_live_dps) / 3600.0 
                    proj_x = last_x + hours_to_kill
                    
                    ax.plot([last_x, proj_x], [last_y, 0], 'r--', linewidth=1.5, alpha=0.9)

        except Exception:
            pass
            
    ax.set_xlim(0, 168); ax.set_ylim(0, 100); canvas.draw_idle()

def start_tracking():
    global start_time, total_seconds_at_start, initial_hp_at_start, tracking_id, history
    if tracking_id: 
        root.after_cancel(tracking_id)
    try:
        start_time = datetime.now()
        total_seconds_at_start = (int(strip_non_numeric(days_entry.get())) * 86400) + \
                                 (int(strip_non_numeric(hours_entry.get())) * 3600) + \
                                 (int(strip_non_numeric(mins_entry.get())) * 60)
        rem_h = int(strip_non_numeric(health_entry.get()))
        rem_h_suffix = int(strip_non_numeric(health_suffix_entry.get()))
        initial_hp_at_start = float(f"{rem_h}{rem_h_suffix:06d}")
        
        tier_val = int(strip_non_numeric(tier_entry.get()))
        dps_val = float(strip_non_numeric(dps_entry.get()))
        total_hp = TIER_DATA[tier_val]["health"]
        percent_left = (initial_hp_at_start / total_hp) * 100
        
        # Calculate elapsed hours from the start of the 168-hour window
        encounter_elapsed_hours = 168 - (total_seconds_at_start / 3600)
        
        # Only append if history is empty or the new time is strictly greater than the last point
        if not history or (encounter_elapsed_hours > (history[-1][0] + 0.001)):
            # Capture the current unique DPS value alongside coordinate variables
            history.append([encounter_elapsed_hours, max(0, percent_left), dps_val])
            update_chart()
        else:
            # If we aren't adding a new point, just refresh the chart with current inputs
            update_chart()
        
        save_all()
        run_update()
    except ValueError: 
        messagebox.showerror("Error", "Check your inputs.")

def run_update():
    global tracking_id, history
    try:
        tier_val = int(strip_non_numeric(tier_entry.get()))
        dps = float(strip_non_numeric(dps_entry.get()))
        elapsed = (datetime.now() - start_time).total_seconds()
        current_time_left = total_seconds_at_start - elapsed
        current_hp = initial_hp_at_start - (dps * elapsed)
        total_hp = TIER_DATA[tier_val]["health"]
        percent_left = (current_hp / total_hp) * 100
        
        # UI Updates
        progress_bar['value'] = percent_left
        progress_label.config(text=f"{max(0, percent_left):.2f}%")
        live_tracking_label.config(text=f"Time left: {format_time_delta(current_time_left)}\nHP left: {int(max(0, current_hp)):,}")
        tier_info = TIER_DATA[tier_val]
        tier_info_label.config(text=f'"{tier_info["name"]}" {tier_info["health"]:,.0f} HP')
        
        if (dps * current_time_left) >= current_hp:
            success_time = (dps * current_time_left - current_hp) / dps if dps > 0 else 0
            status_label.config(text=f"On track to WIN!\nAhead by: {format_time_delta(success_time)}", fg="dark green")
        else:
            delay = (current_hp / dps) - current_time_left if dps > 0 else float('inf')
            
            deficit = current_hp - (dps * current_time_left)
            needed_dps = deficit / current_time_left if current_time_left > 0 else 0
            
            status_label.config(text=f"Projected to FAIL.\nNeed {needed_dps:,.0f} additional DPS.\nLate by: {format_time_delta(delay)}", fg="red")
        
        tracking_id = root.after(1000, run_update)
    except: 
        pass

# GUI setup
root = tk.Tk()
root.title("ToMT Tier Progress Calculator")
root.geometry("600x650")
root.minsize(500, 550)

root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(2, weight=1)
root.columnconfigure(3, weight=1)
root.rowconfigure(7, weight=1) 

# Inputs
tk.Label(root, text="Tier (1-10):").grid(row=0, column=0, sticky="e"); tier_entry = tk.Entry(root, width=10); tier_entry.grid(row=0, column=1, sticky="w")
tk.Label(root, text="Total DPS:").grid(row=0, column=2, sticky="e"); dps_entry = tk.Entry(root, width=15); dps_entry.grid(row=0, column=3, sticky="w")
tk.Label(root, text="Remaining HP:").grid(row=1, column=0, sticky="e"); health_entry = tk.Entry(root, width=10); health_entry.grid(row=1, column=1, sticky="w")
health_suffix_entry = tk.Entry(root, width=8); health_suffix_entry.grid(row=1, column=2, sticky="w", padx=5)

time_frame = tk.Frame(root); time_frame.grid(row=2, column=1, columnspan=2, sticky="w")
days_entry = tk.Entry(time_frame, width=3); days_entry.pack(side=tk.LEFT); tk.Label(time_frame, text=" d ").pack(side=tk.LEFT)
hours_entry = tk.Entry(time_frame, width=3); hours_entry.pack(side=tk.LEFT); tk.Label(time_frame, text=" h ").pack(side=tk.LEFT)
mins_entry = tk.Entry(time_frame, width=3); mins_entry.pack(side=tk.LEFT); tk.Label(time_frame, text=" m ").pack(side=tk.LEFT)

# Button Frame
button_frame = tk.Frame(root)
button_frame.grid(row=3, column=0, columnspan=4, pady=5)
tk.Button(button_frame, text="Calculate", command=start_tracking, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="ReLoad Chart", command=reload_chart, width=15, fg="red").pack(side=tk.LEFT, padx=5)

live_tracking_label = tk.Label(root, text="Time left: --\nHP left: --", font=("Arial", 10), bg="lightyellow", highlightthickness=1)
live_tracking_label.grid(row=4, column=0, columnspan=4, pady=5)
tier_info_label = tk.Label(root, text="", font=("Arial", 10, "bold")); tier_info_label.grid(row=5, column=0, columnspan=4)

status_label = tk.Label(root, text="", font=("Arial", 10, "bold"), justify="center"); status_label.grid(row=6, column=0, columnspan=4)

# Matplotlib Chart
fig = plt.Figure(figsize=(5, 3), dpi=100); ax = fig.add_subplot(111); canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=7, column=0, columnspan=4, sticky="nsew", padx=10, pady=5)

# Progress Bar
style = ttk.Style(); style.theme_use('default'); style.configure("Black.Horizontal.TProgressbar", background="green", troughcolor="black", borderwidth=0, thickness=30)
progress_container = tk.Frame(root, bg="white"); progress_container.grid(row=8, column=0, columnspan=4, sticky="ew", pady=7, padx=10)
progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=300, mode="determinate", style="Black.Horizontal.TProgressbar")
progress_bar.pack(fill="x", expand=True)
progress_label = tk.Label(progress_container, text="0.00%", fg="white", bg="black", font=("Arial", 8)); progress_label.place(relx=0.98, rely=0.5, anchor="e")

load_all()
root.mainloop()
