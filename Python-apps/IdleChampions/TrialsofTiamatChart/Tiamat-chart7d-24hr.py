import re, json, os, glob, math, warnings
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MultipleLocator
import numpy as np

# Suppress expected numpy slice warnings for incomplete plot spans
warnings.filterwarnings("ignore", category=RuntimeWarning, message="All-NaN slice encountered")

# Tier to Health Mapping
TIER_DATA = {
    1: {"name": "Normal", "health": 4.00e08}, 2: {"name": "Heroic", "health": 7.50e08},
    3: {"name": "Master", "health": 1.30e09}, 4: {"name": "Legend", "health": 2.00e09},
    5: {"name": "Torment", "health": 2.90e09}, 6: {"name": "Grand Master", "health": 4.30e09},
    7: {"name": "Grand Legend", "health": 6.10e09}, 8: {"name": "Grand Torment", "health": 8.60e09},
    9: {"name": "Exalted Master", "health": 12.00e09}, 10: {"name": "Exalted Legend", "health": 16.00e09}
}

SETTINGS_FILE = "settings.json"
PLOT_DIR = "plot_data"

history = [] 
tracking_id = None
pulse_id = None
day_blink_id = None
victory_blink_id = None

start_time = None
total_seconds_at_start = 0
initial_hp_at_start = 0

pulse_alpha = 0.6
pulse_direction = 1

# State flags for indicators
day_indicator_acknowledged_day = -1
day_blink_state = False
victory_blink_state = False

def ensure_plot_dir():
    if not os.path.exists(PLOT_DIR):
        os.makedirs(PLOT_DIR)

def get_current_plot_filepath():
    ensure_plot_dir()
    today_str = datetime.now().strftime("%Y_%m_%d")
    return os.path.join(PLOT_DIR, f"plot_data_{today_str}.json")

def strip_non_numeric(val): 
    return re.sub(r'\D', '', str(val))

def format_time_delta(seconds):
    delta = timedelta(seconds=int(max(0, seconds)))
    return f"{delta.days}d {delta.seconds // 3600}h {(delta.seconds // 60) % 60}m"

def save_all():
    ensure_plot_dir()
    data = {
        "tier": tier_entry.get(), "dps": dps_entry.get(), 
        "hp_main": health_entry.get(), "hp_sub": health_suffix_entry.get(), 
        "d": days_entry.get(), "h": hours_entry.get(), "m": mins_entry.get(),
        "start_time": start_time.isoformat() if start_time else None,
        "total_seconds_at_start": total_seconds_at_start,
        "initial_hp_at_start": initial_hp_at_start
    }
    with open(SETTINGS_FILE, "w") as f: 
        json.dump(data, f)
    
    current_file = get_current_plot_filepath()
    with open(current_file, "w") as f: 
        json.dump(history, f)

def load_all():
    global history, start_time, total_seconds_at_start, initial_hp_at_start
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                data = json.load(f)
                block_trace_handlers(True)
                
                tier_entry.delete(0, tk.END); tier_entry.insert(0, data.get("tier", "9"))
                dps_entry.delete(0, tk.END); dps_entry.insert(0, data.get("dps", "35160"))
                health_entry.delete(0, tk.END); health_entry.insert(0, data.get("hp_main", "3483"))
                health_suffix_entry.delete(0, tk.END); health_suffix_entry.insert(0, data.get("hp_sub", "000000"))
                days_entry.delete(0, tk.END); days_entry.insert(0, data.get("d", "3"))
                hours_entry.delete(0, tk.END); hours_entry.insert(0, data.get("h", "4"))
                mins_entry.delete(0, tk.END); mins_entry.insert(0, data.get("m", "46"))
                
                block_trace_handlers(False)
                
                saved_start = data.get("start_time")
                if saved_start:
                    start_time = datetime.fromisoformat(saved_start)
                    total_seconds_at_start = data.get("total_seconds_at_start", 0)
                    initial_hp_at_start = data.get("initial_hp_at_start", 0)
            except: 
                block_trace_handlers(False)
    
    current_file = get_current_plot_filepath()
    if os.path.exists(current_file):
        try:
            with open(current_file, "r") as f:
                history = json.load(f)
        except: 
            history = []
    elif os.path.exists("plot_data.json"):
        try:
            with open("plot_data.json", "r") as f:
                history = json.load(f)
        except: 
            history = []
    else:
        history = []
        
    update_chart()
    if start_time:
        run_update()

def reload_chart():
    load_all()
    messagebox.showinfo("Success", "Chart and data reloaded successfully.")

def load_all_historical_runs():
    """Scans all json files in /plot_data/ and returns interpolated min/max arrays over 0-168 hours."""
    ensure_plot_dir()
    files = glob.glob(os.path.join(PLOT_DIR, "plot_data_*.json"))
    if os.path.exists("plot_data.json"):
        files.append("plot_data.json")
        
    if not files:
        return None, None, None

    grid_x = np.linspace(0, 168, 500)
    all_interpolated = []

    for filepath in set(files):
        try:
            with open(filepath, "r") as f:
                run_data = json.load(f)
                if not run_data or len(run_data) < 2:
                    continue
                
                rx = [pt[0] for pt in run_data]
                ry = [pt[1] for pt in run_data]

                sort_idx = np.argsort(rx)
                rx_sorted = np.array(rx)[sort_idx]
                ry_sorted = np.array(ry)[sort_idx]

                unique_x, unique_indices = np.unique(rx_sorted, return_index=True)
                unique_y = ry_sorted[unique_indices]

                if len(unique_x) >= 2:
                    valid_mask = (grid_x >= unique_x[0]) & (grid_x <= unique_x[-1])
                    interp_y = np.full_like(grid_x, np.nan)
                    interp_y[valid_mask] = np.interp(grid_x[valid_mask], unique_x, unique_y)
                    all_interpolated.append(interp_y)
        except Exception:
            continue

    if not all_interpolated:
        return None, None, None

    all_array = np.array(all_interpolated)
    
    with np.errstate(all='ignore'):
        min_y = np.nanmin(all_array, axis=0)
        max_y = np.nanmax(all_array, axis=0)
    
    return grid_x, min_y, max_y

def get_current_ui_coordinates():
    try:
        t_val = int(strip_non_numeric(tier_entry.get()))
        dps_val = float(strip_non_numeric(dps_entry.get()))
        rem_h = int(strip_non_numeric(health_entry.get()))
        rem_h_sub = int(strip_non_numeric(health_suffix_entry.get()))
        hp_val = float(f"{rem_h}{rem_h_sub:06d}")
        
        d_val = int(strip_non_numeric(days_entry.get()))
        h_val = int(strip_non_numeric(hours_entry.get()))
        m_val = int(strip_non_numeric(mins_entry.get()))
        
        tot_sec = (d_val * 86400) + (h_val * 3600) + (m_val * 60)
        x_hours = 168 - (tot_sec / 3600.0)
        
        total_hp = TIER_DATA[t_val]["health"]
        y_percent = (hp_val / total_hp) * 100.0
        
        return x_hours, max(0.0, y_percent), dps_val, total_hp
    except:
        return None

def update_chart():
    ax.clear()
    ax.yaxis.tick_right()
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])
    ax.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
    ax.xaxis.set_minor_locator(MultipleLocator(12))

    gx, min_y, max_y = load_all_historical_runs()
    if gx is not None:
        ax.fill_between(gx, min_y, max_y, color='#D3D3D3', alpha=0.5, zorder=0.5, label='Historical Range')

    for hour in [24, 48, 72, 96, 120, 144]:
        ax.axvline(x=hour, color='#FDF4A9', linestyle='-', linewidth=1, zorder=1)
        
    current_live_dps = 0.0
    try:
        current_live_dps = float(strip_non_numeric(dps_entry.get()))
    except:
        pass

    if history:
        x_vals = [p[0] for p in history]
        y_vals = [p[1] for p in history]
        ax.plot(x_vals, y_vals, 'g-o', zorder=3)
        
        try:
            tier_val = int(strip_non_numeric(tier_entry.get()))
            total_hp = TIER_DATA[tier_val]["health"]
            
            for i in range(len(history)):
                pt_x = history[i][0]
                pt_y = history[i][1]
                
                if len(history[i]) > 2:
                    pt_dps = float(history[i][2])
                else:
                    pt_dps = current_live_dps
                
                if pt_dps > 0 and pt_y > 0:
                    remaining_hp_at_point = (pt_y / 100.0) * total_hp
                    hours_to_kill = (remaining_hp_at_point / pt_dps) / 3600.0
                    proj_x = pt_x + hours_to_kill
                    ax.plot([pt_x, proj_x], [pt_y, 0], 'r:', linewidth=1, alpha=0.5, zorder=2)

            last_x = history[-1][0]
            last_y = history[-1][1]
            last_dps = float(history[-1][2]) if len(history[-1]) > 2 else current_live_dps
                
            if last_dps > 0 and last_y > 0:
                remaining_hp = (last_y / 100.0) * total_hp
                hours_to_kill = (remaining_hp / last_dps) / 3600.0 
                proj_x = last_x + hours_to_kill
                ax.plot([last_x, proj_x], [last_y, 0], 'r--', linewidth=1.5, alpha=0.9, zorder=2)
                
            if start_time and last_dps > 0:
                elapsed_seconds = (datetime.now() - start_time).total_seconds()
                live_x_hours = 168 - ((total_seconds_at_start - elapsed_seconds) / 3600.0)
                
                if 0 <= live_x_hours <= 168:
                    hours_since_last_saved = live_x_hours - last_x
                    remaining_hp_at_last_saved = (last_y / 100.0) * total_hp
                    
                    projected_hp_now = remaining_hp_at_last_saved - (last_dps * hours_since_last_saved * 3600.0)
                    live_y_percent = (projected_hp_now / total_hp) * 100.0
                    live_y_percent = max(0.0, min(100.0, live_y_percent))
                    
                    ax.axhline(y=live_y_percent, color='#AEAEAE', linestyle='-', linewidth=0.8, alpha=0.7, zorder=1)
                    ax.axvline(x=live_x_hours, color='#AEAEAE', linestyle='-', linewidth=0.8, alpha=0.7, zorder=1)
                    
        except Exception:
            pass

    ui_coords = get_current_ui_coordinates()
    if ui_coords and history:
        ui_x, ui_y, ui_dps, total_hp = ui_coords
        last_pt = history[-1]
        
        is_matching_x = abs(ui_x - last_pt[0]) < 0.001
        is_matching_y = abs(ui_y - last_pt[1]) < 0.001
        is_matching_dps = abs(ui_dps - last_pt[2]) < 0.001 if len(last_pt) > 2 else True

        if not (is_matching_x and is_matching_y and is_matching_dps):
            ax.plot(ui_x, ui_y, 'bo', alpha=pulse_alpha, markersize=8, zorder=4)
            if ui_dps > 0 and ui_y > 0:
                rem_hp_staging = (ui_y / 100.0) * total_hp
                h_to_kill_staging = (rem_hp_staging / ui_dps) / 3600.0
                staging_proj_x = ui_x + h_to_kill_staging
                ax.plot([ui_x, staging_proj_x], [ui_y, 0], 'b:', linewidth=1.5, alpha=0.6, zorder=2)
                
    ax.set_xlim(0, 168)
    ax.set_ylim(0, 100)
    canvas.draw_idle()

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
        
        encounter_elapsed_hours = 168 - (total_seconds_at_start / 3600)
        
        if not history or (encounter_elapsed_hours > (history[-1][0] + 0.001)):
            history.append([encounter_elapsed_hours, max(0, percent_left), dps_val])
            update_chart()
        else:
            update_chart()
        
        save_all()
        run_update()
    except ValueError: 
        messagebox.showerror("Error", "Check your inputs.")

def update_day_indicator(current_time_left_seconds):
    global day_indicator_acknowledged_day, day_blink_state
    current_days_remaining = math.floor(current_time_left_seconds / 86400)
    
    if day_indicator_acknowledged_day == -1:
        day_indicator_acknowledged_day = current_days_remaining

    if current_days_remaining < day_indicator_acknowledged_day:
        day_blink_state = not day_blink_state
        fill_color = "red" if day_blink_state else "yellow"
        day_canvas.itemconfig(day_circle_id, fill=fill_color)
    else:
        day_canvas.itemconfig(day_circle_id, fill="green")

def on_day_indicator_click(event):
    global day_indicator_acknowledged_day
    try:
        elapsed = (datetime.now() - start_time).total_seconds()
        current_time_left = total_seconds_at_start - elapsed
        day_indicator_acknowledged_day = math.floor(current_time_left / 86400)
        day_canvas.itemconfig(day_circle_id, fill="green")
    except:
        pass

def run_update():
    global tracking_id, history, victory_blink_state
    try:
        tier_val = int(strip_non_numeric(tier_entry.get()))
        dps = float(strip_non_numeric(dps_entry.get()))
        elapsed = (datetime.now() - start_time).total_seconds()
        current_time_left = total_seconds_at_start - elapsed
        current_hp = initial_hp_at_start - (dps * elapsed)
        total_hp = TIER_DATA[tier_val]["health"]
        percent_left = (current_hp / total_hp) * 100.0
        
        progress_bar['value'] = max(0, percent_left)
        progress_label.config(text=f"{max(0, percent_left):.2f}%")
        live_tracking_label.config(text=f"Time left: {format_time_delta(current_time_left)}\nHP left: {int(max(0, current_hp)):,}")
        
        tier_info = TIER_DATA[tier_val]
        tier_info_label.config(text=f'"{tier_info["name"]}" {tier_info["health"]:,.0f} HP')
        
        update_day_indicator(current_time_left)

        if current_hp <= 0 or percent_left <= 0:
            status_label.config(text="TIAMAT DEFEATED!", fg="gold")
            victory_blink_state = not victory_blink_state
            style.configure("Black.Horizontal.TProgressbar", background="red" if victory_blink_state else "black")
        else:
            style.configure("Black.Horizontal.TProgressbar", background="green")
            if (dps * current_time_left) >= current_hp:
                success_time = (dps * current_time_left - current_hp) / dps if dps > 0 else 0
                status_label.config(text=f"On track to WIN!\nWin in: {format_time_delta(current_time_left-success_time)}", fg="dark green")
            else:
                delay = (current_hp / dps) - current_time_left if dps > 0 else float('inf')
                deficit = current_hp - (dps * current_time_left)
                needed_dps = deficit / current_time_left if current_time_left > 0 else 0
                status_label.config(text=f"Projected to FAIL.\nNeed {needed_dps:,.0f} additional DPS.\nLate by: {format_time_delta(delay)}", fg="red")
        
        update_chart()
        tracking_id = root.after(1000, run_update)
    except: 
        pass

def animate_pulse():
    global pulse_alpha, pulse_direction, pulse_id
    
    if pulse_direction == 1:
        pulse_alpha += 0.04
        if pulse_alpha >= 0.95:
            pulse_alpha = 0.95
            pulse_direction = -1
    else:
        pulse_alpha -= 0.04
        if pulse_alpha <= 0.35:
            pulse_alpha = 0.35
            pulse_direction = 1
            
    ui_coords = get_current_ui_coordinates()
    if ui_coords and history:
        ui_x, ui_y, ui_dps, _ = ui_coords
        last_pt = history[-1]
        is_matching_x = abs(ui_x - last_pt[0]) < 0.001
        is_matching_y = abs(ui_y - last_pt[1]) < 0.001
        is_matching_dps = abs(ui_dps - last_pt[2]) < 0.001 if len(last_pt) > 2 else True
            
        if not (is_matching_x and is_matching_y and is_matching_dps):
            update_chart()
            
    pulse_id = root.after(60, animate_pulse)

def on_input_changed(*args):
    update_chart()

def block_trace_handlers(should_block):
    global tier_trace_id, dps_trace_id, hp_trace_id, hp_sub_trace_id, d_trace_id, h_trace_id, m_trace_id
    
    if should_block:
        tier_var.trace_remove('write', tier_trace_id)
        dps_var.trace_remove('write', dps_trace_id)
        hp_var.trace_remove('write', hp_trace_id)
        hp_sub_var.trace_remove('write', hp_sub_trace_id)
        d_var.trace_remove('write', d_trace_id)
        h_var.trace_remove('write', h_trace_id)
        m_var.trace_remove('write', m_trace_id)
    else:
        tier_trace_id = tier_var.trace_add('write', on_input_changed)
        dps_trace_id = dps_var.trace_add('write', on_input_changed)
        hp_trace_id = hp_var.trace_add('write', on_input_changed)
        hp_sub_trace_id = hp_sub_var.trace_add('write', on_input_changed)
        d_trace_id = d_var.trace_add('write', on_input_changed)
        h_trace_id = h_var.trace_add('write', on_input_changed)
        m_trace_id = m_var.trace_add('write', on_input_changed)

# --- GUI SETUP ---
root = tk.Tk()
root.title("ToMT Tier Progress Calculator")
root.geometry("600x650")
root.minsize(500, 550)

# Main Controls Layout Container
input_frame = tk.Frame(root)
input_frame.grid(row=0, column=0, columnspan=4, pady=10)

tier_var = tk.StringVar(value="9")
dps_var = tk.StringVar(value="35160")
hp_var = tk.StringVar(value="3483")
hp_sub_var = tk.StringVar(value="000000")
d_var = tk.StringVar(value="3")
h_var = tk.StringVar(value="4")
m_var = tk.StringVar(value="46")

# Row 0: Tier & Total DPS (Grouped left)
tk.Label(input_frame, text="Tier (1-10):").grid(row=0, column=0, sticky="e", padx=(0,2))
tier_entry = tk.Entry(input_frame, width=8, textvariable=tier_var)
tier_entry.grid(row=0, column=1, sticky="w", padx=(0,15))

tk.Label(input_frame, text="Total DPS:").grid(row=0, column=2, sticky="e", padx=(0,2))
dps_entry = tk.Entry(input_frame, width=12, textvariable=dps_var)
dps_entry.grid(row=0, column=3, sticky="w")

# Row 1: Remaining HP Main & Suffix Box (Grouped left)
tk.Label(input_frame, text="Remaining HP:").grid(row=1, column=0, sticky="e", padx=(0,2), pady=3)
health_entry = tk.Entry(input_frame, width=8, textvariable=hp_var)
health_entry.grid(row=1, column=1, sticky="w", padx=(0,15), pady=3)

health_suffix_entry = tk.Entry(input_frame, width=8, textvariable=hp_sub_var)
health_suffix_entry.grid(row=1, column=2, columnspan=2, sticky="w", pady=3)

# Row 2: Days / Hours / Mins Duration Controls
time_frame = tk.Frame(input_frame)
time_frame.grid(row=2, column=1, columnspan=3, sticky="w", pady=3)

days_entry = tk.Entry(time_frame, width=3, textvariable=d_var)
days_entry.pack(side=tk.LEFT)
tk.Label(time_frame, text=" d ").pack(side=tk.LEFT)

hours_entry = tk.Entry(time_frame, width=3, textvariable=h_var)
hours_entry.pack(side=tk.LEFT)
tk.Label(time_frame, text=" h ").pack(side=tk.LEFT)

mins_entry = tk.Entry(time_frame, width=3, textvariable=m_var)
mins_entry.pack(side=tk.LEFT)
tk.Label(time_frame, text=" m ").pack(side=tk.LEFT)

# Bind Trace Handlers
tier_trace_id = tier_var.trace_add('write', on_input_changed)
dps_trace_id = dps_var.trace_add('write', on_input_changed)
hp_trace_id = hp_var.trace_add('write', on_input_changed)
hp_sub_trace_id = hp_sub_var.trace_add('write', on_input_changed)
d_trace_id = d_var.trace_add('write', on_input_changed)
h_trace_id = h_var.trace_add('write', on_input_changed)
m_trace_id = m_var.trace_add('write', on_input_changed)

# Action Buttons
button_frame = tk.Frame(root)
button_frame.grid(row=3, column=0, columnspan=4, pady=5)
tk.Button(button_frame, text="Calculate", command=start_tracking, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="ReLoad Chart", command=reload_chart, width=15, fg="red").pack(side=tk.LEFT, padx=5)

# Live Tracking Display & Day Indicator
tracking_container = tk.Frame(root)
tracking_container.grid(row=4, column=0, columnspan=4, pady=5)

live_tracking_label = tk.Label(tracking_container, text="Time left: --\nHP left: --", font=("Arial", 10), bg="lightyellow", highlightthickness=1)
live_tracking_label.pack(side=tk.LEFT, padx=5)

day_canvas = tk.Canvas(tracking_container, width=24, height=24, highlightthickness=0)
day_canvas.pack(side=tk.LEFT, padx=5)
day_circle_id = day_canvas.create_oval(3, 3, 21, 21, fill="green", outline="black")
day_canvas.bind("<Button-1>", on_day_indicator_click)

# Labels
tier_info_label = tk.Label(root, text="", font=("Arial", 10, "bold"))
tier_info_label.grid(row=5, column=0, columnspan=4)

status_label = tk.Label(root, text="", font=("Arial", 10, "bold"), justify="center")
status_label.grid(row=6, column=0, columnspan=4)

# Matplotlib Chart
root.rowconfigure(7, weight=1)
root.columnconfigure(0, weight=1)

fig = plt.Figure(figsize=(5, 3), dpi=100)
ax = fig.add_subplot(111)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=7, column=0, columnspan=4, sticky="nsew", padx=10, pady=5)

# Progress Bar
style = ttk.Style()
style.theme_use('default')
style.configure("Black.Horizontal.TProgressbar", background="green", troughcolor="black", borderwidth=0, thickness=30)

progress_container = tk.Frame(root, bg="white")
progress_container.grid(row=8, column=0, columnspan=4, sticky="ew", pady=7, padx=10)
progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=300, mode="determinate", style="Black.Horizontal.TProgressbar")
progress_bar.pack(fill="x", expand=True)
progress_label = tk.Label(progress_container, text="0.00%", fg="white", bg="black", font=("Arial", 8))
progress_label.place(relx=0.98, rely=0.5, anchor="e")

load_all()
animate_pulse() 
root.mainloop()