import glob
import json
import math
import os
import re
import warnings
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MultipleLocator
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk

# Suppress expected numpy slice warnings for incomplete plot spans
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message="All-NaN slice encountered"
)

# Tier to Health Mapping
TIER_DATA = {
    1: {"name": "Normal", "health": 4.00e08},
    2: {"name": "Heroic", "health": 7.50e08},
    3: {"name": "Master", "health": 1.30e09},
    4: {"name": "Legend", "health": 2.00e09},
    5: {"name": "Torment", "health": 2.90e09},
    6: {"name": "Grand Master", "health": 4.30e09},
    7: {"name": "Grand Legend", "health": 6.10e09},
    8: {"name": "Grand Torment", "health": 8.60e09},
    9: {"name": "Exalted Master", "health": 12.00e09},
    10: {"name": "Exalted Legend", "health": 16.00e09},
}

SETTINGS_FILE = "settings.json"
PLOT_DIR = "plot_data"

history = []
tracking_id = None
resize_timer_id = None

start_time = None
total_seconds_at_start = 0
initial_hp_at_start = 0

# Static translucency for crosshair indicator dot
STATIC_DOT_ALPHA = 0.45

# State flags for indicators
day_indicator_acknowledged_day = -1
day_blink_state = False

# Zoom state tracking
current_x_range = [0, 168]
current_y_range = [0, 100]

# Historical Data Cache
CACHED_HISTORICAL_RUNS = None
LAST_PROGRESS_PCTS = (0.0, 0.0)


def ensure_plot_dir():
  if not os.path.exists(PLOT_DIR):
    os.makedirs(PLOT_DIR)


def get_current_plot_filepath():
  ensure_plot_dir()
  week_str = datetime.now().strftime("%Y_W%U")
  return os.path.join(PLOT_DIR, f"plot_data_{week_str}.json")


def strip_non_numeric(val):
  return re.sub(r"\D", "", str(val))


def format_time_delta(seconds):
  delta = timedelta(seconds=int(max(0, seconds)))
  return f"{delta.days}d {delta.seconds // 3600}h {(delta.seconds // 60) % 60}m"


def save_all():
  ensure_plot_dir()
  data = {
      "tier": tier_entry.get(),
      "dps": dps_entry.get(),
      "hp_main": health_entry.get(),
      "hp_sub": health_suffix_entry.get(),
      "d": days_entry.get(),
      "h": hours_entry.get(),
      "m": mins_entry.get(),
      "start_time": start_time.isoformat() if start_time else None,
      "total_seconds_at_start": total_seconds_at_start,
      "initial_hp_at_start": initial_hp_at_start,
  }
  with open(SETTINGS_FILE, "w") as f:
    json.dump(data, f)

  current_file = get_current_plot_filepath()
  with open(current_file, "w") as f:
    json.dump(history, f)
  
  # Invalidate history cache so new points update historical averages
  global CACHED_HISTORICAL_RUNS
  CACHED_HISTORICAL_RUNS = None


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


def load_all_historical_runs():
  global CACHED_HISTORICAL_RUNS
  if CACHED_HISTORICAL_RUNS is not None:
    return CACHED_HISTORICAL_RUNS

  ensure_plot_dir()
  files = glob.glob(os.path.join(PLOT_DIR, "*.json"))
  if not files:
    CACHED_HISTORICAL_RUNS = (None, None, None)
    return CACHED_HISTORICAL_RUNS

  all_runs = []
  for filepath in files:
    try:
      with open(filepath, "r") as f:
        data = json.load(f)
        if data and isinstance(data, list):
          all_runs.append(data)
    except Exception:
      continue

  if not all_runs:
    CACHED_HISTORICAL_RUNS = (None, None, None)
    return CACHED_HISTORICAL_RUNS

  gx = np.linspace(0, 168, 500)
  interpolated_y_list = []

  for run in all_runs:
    if not run:
      continue
    rx = [pt[0] for pt in run]
    ry = [pt[1] for pt in run]

    iy = np.interp(gx, rx, ry, left=np.nan, right=np.nan)
    interpolated_y_list.append(iy)

  if not interpolated_y_list:
    CACHED_HISTORICAL_RUNS = (None, None, None)
    return CACHED_HISTORICAL_RUNS

  y_matrix = np.array(interpolated_y_list)

  with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    min_y = np.nanmin(y_matrix, axis=0)
    max_y = np.nanmax(y_matrix, axis=0)

  CACHED_HISTORICAL_RUNS = (gx, min_y, max_y)
  return CACHED_HISTORICAL_RUNS


def draw_gauge_gradient():
  gauge_canvas.delete("all")
  w, h = 30, 110

  colors = [(255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 180, 0)]

  for y in range(h):
    t = y / (h - 1)
    if t <= 0.333:
      sub_t = t / 0.333
      c1, c2 = colors[0], colors[1]
    elif t <= 0.666:
      sub_t = (t - 0.333) / 0.333
      c1, c2 = colors[1], colors[2]
    else:
      sub_t = (t - 0.666) / 0.334
      c1, c2 = colors[2], colors[3]

    r = int(c1[0] + (c2[0] - c1[0]) * sub_t)
    g = int(c1[1] + (c2[1] - c1[1]) * sub_t)
    b = int(c1[2] + (c2[2] - c1[2]) * sub_t)

    gauge_canvas.create_line(0, y, w, y, fill=f"#{r:02x}{g:02x}{b:02x}")

  gauge_canvas.create_rectangle(0, 0, w - 1, h - 1, outline="black", width=2)


def update_performance_gauge(current_x, current_y):
  gx, min_y, max_y = load_all_historical_runs()

  draw_gauge_gradient()

  if gx is None or len(gx) == 0:
    gauge_label.config(text="--", fg="black")
    return

  hist_min = np.interp(current_x, gx, min_y)
  hist_max = np.interp(current_x, gx, max_y)

  if np.isnan(hist_min) or np.isnan(hist_max) or hist_min == hist_max:
    gauge_label.config(text="--", fg="black")
    return

  rel_pos = (current_y - hist_min) / (hist_max - hist_min)

  h = 110
  clamped_pos = max(-0.15, min(1.15, rel_pos))
  y_pixel = int((1.0 - clamped_pos) * h)
  y_pixel = max(3, min(h - 3, y_pixel))

  gauge_canvas.create_rectangle(
      0, y_pixel - 3, 30, y_pixel + 3, fill="black", outline="white"
  )

  if rel_pos < 0.0:
    status_str, status_color = "BEST", "darkgreen"
  elif rel_pos <= 0.25:
    status_str, status_color = "Great", "green"
  elif rel_pos <= 0.50:
    status_str, status_color = "Good", "#8B8000"
  elif rel_pos <= 0.75:
    status_str, status_color = "Average", "orange"
  elif rel_pos <= 1.0:
    status_str, status_color = "Poor", "red"
  else:
    status_str, status_color = "WORST", "darkred"

  gauge_label.config(text=status_str, fg=status_color)


def draw_custom_progress_bar(current_pct, proj_pct):
  global LAST_PROGRESS_PCTS
  LAST_PROGRESS_PCTS = (current_pct, proj_pct)

  progress_canvas.delete("all")
  w = progress_canvas.winfo_width()
  h = progress_canvas.winfo_height()

  if w <= 1:
    w = 560
  if h <= 1:
    h = 30

  progress_canvas.create_rectangle(0, 0, w, h, fill="black", outline="")

  if current_pct > 0:
    green_w = int((min(100.0, max(0.0, current_pct)) / 100.0) * w)
    progress_canvas.create_rectangle(
        0, 0, green_w, h, fill="green", outline=""
    )

  if proj_pct > 0:
    proj_w = int((min(100.0, max(0.0, proj_pct)) / 100.0) * w)
    progress_canvas.create_rectangle(
        0, 0, proj_w, h, fill="#FF7F27", outline=""
    )

    progress_canvas.create_text(
        8,
        h / 2,
        text=f"{proj_pct:.2f}%",
        fill="white",
        anchor="w",
        font=("Arial", 9, "bold"),
    )

  progress_canvas.create_text(
      w - 8,
      h / 2,
      text=f"{max(0.0, current_pct):.2f}%",
      fill="white",
      anchor="e",
      font=("Arial", 9, "bold"),
  )


def zoom_in():
  global current_x_range, current_y_range

  span_x = current_x_range[1] - current_x_range[0]
  new_span_x = max(4, span_x / 2.0)

  target_center_x = current_x_range[0] + (span_x * 0.25)
  new_min_x = max(0, target_center_x - (new_span_x / 2.0))
  new_max_x = min(168, new_min_x + new_span_x)

  if new_min_x == 0:
    new_max_x = min(168, new_span_x)
  current_x_range = [new_min_x, new_max_x]

  span_y = current_y_range[1] - current_y_range[0]
  new_span_y = max(5, span_y / 2.0)

  target_center_y = current_y_range[0] + (span_y * 0.75)
  new_max_y = min(100, target_center_y + (new_span_y / 2.0))
  new_min_y = max(0, new_max_y - new_span_y)

  if new_max_y == 100:
    new_min_y = max(0, 100 - new_span_y)
  current_y_range = [new_min_y, new_max_y]

  update_chart()


def zoom_out():
  global current_x_range, current_y_range
  span_x = current_x_range[1] - current_x_range[0]
  new_span_x = min(168, span_x * 2.0)
  center_x = (current_x_range[0] + current_x_range[1]) / 2.0
  new_min_x = max(0, center_x - (new_span_x / 2.0))
  new_max_x = min(168, new_min_x + new_span_x)
  if new_max_x == 168:
    new_min_x = max(0, 168 - new_span_x)
  current_x_range = [new_min_x, new_max_x]

  span_y = current_y_range[1] - current_y_range[0]
  new_span_y = min(100, span_y * 2.0)
  center_y = (current_y_range[0] + current_y_range[1]) / 2.0
  new_min_y = max(0, center_y - (new_span_y / 2.0))
  new_max_y = min(100, new_min_y + new_span_y)
  if new_max_y == 100:
    new_min_y = max(0, 100 - new_span_y)
  current_y_range = [new_min_y, new_max_y]

  update_chart()


def zoom_reset():
  global current_x_range, current_y_range
  current_x_range = [0, 168]
  current_y_range = [0, 100]
  update_chart()


def update_chart():
  ax.clear()
  ax.yaxis.tick_right()

  y_span = current_y_range[1] - current_y_range[0]
  if y_span <= 10:
    ax.yaxis.set_major_locator(MultipleLocator(1))
  elif y_span <= 25:
    ax.yaxis.set_major_locator(MultipleLocator(5))
  else:
    ax.yaxis.set_major_locator(MultipleLocator(20))

  ax.yaxis.set_major_formatter(
      plt.FuncFormatter(
          lambda val, loc: f"{val:.1f}%" if y_span <= 10 else f"{int(val)}%"
      )
  )

  x_span = current_x_range[1] - current_x_range[0]
  if x_span <= 12:
    ax.xaxis.set_major_locator(MultipleLocator(2))
    ax.xaxis.set_minor_locator(MultipleLocator(0.5))
  elif x_span <= 48:
    ax.xaxis.set_major_locator(MultipleLocator(6))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
  else:
    ax.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
    ax.xaxis.set_minor_locator(MultipleLocator(12))

  gx, min_y, max_y = load_all_historical_runs()
  if gx is not None:
    ax.fill_between(
        gx,
        min_y,
        max_y,
        color="#D3D3D3",
        alpha=0.5,
        zorder=0.5,
        label="Historical Range",
    )

  for hour in range(24, 168, 24):
    ax.axvline(x=hour, color="#FDF4A9", linestyle="-", linewidth=1, zorder=1)

  current_live_dps = 0.0
  try:
    current_live_dps = float(strip_non_numeric(dps_entry.get()))
  except:
    pass

  if history:
    x_vals = [p[0] for p in history]
    y_vals = [p[1] for p in history]
    ax.plot(x_vals, y_vals, "g-o", zorder=3)

    try:
      tier_val = int(strip_non_numeric(tier_entry.get()))
      total_hp = TIER_DATA[tier_val]["health"]

      for i in range(len(history)):
        pt_x = history[i][0]
        pt_y = history[i][1]
        pt_dps = (
            float(history[i][2]) if len(history[i]) > 2 else current_live_dps
        )

        if pt_dps > 0 and pt_y > 0:
          remaining_hp_at_point = (pt_y / 100.0) * total_hp
          hours_to_kill = (remaining_hp_at_point / pt_dps) / 3600.0
          proj_x = pt_x + hours_to_kill
          ax.plot(
              [pt_x, proj_x], [pt_y, 0], "r:", linewidth=1, alpha=0.5, zorder=2
          )

      last_x = history[-1][0]
      last_y = history[-1][1]
      last_dps = (
          float(history[-1][2]) if len(history[-1]) > 2 else current_live_dps
      )

      if last_dps > 0 and last_y > 0:
        remaining_hp = (last_y / 100.0) * total_hp
        hours_to_kill = (remaining_hp / last_dps) / 3600.0
        proj_x = last_x + hours_to_kill
        ax.plot(
            [last_x, proj_x],
            [last_y, 0],
            "r--",
            linewidth=1.5,
            alpha=0.9,
            zorder=2,
        )

      if start_time and last_dps > 0:
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        live_x_hours = 168 - (
            (total_seconds_at_start - elapsed_seconds) / 3600.0
        )

        if 0 <= live_x_hours <= 168:
          hours_since_last_saved = live_x_hours - last_x
          remaining_hp_at_last_saved = (last_y / 100.0) * total_hp

          projected_hp_now = remaining_hp_at_last_saved - (
              last_dps * hours_since_last_saved * 3600.0
          )
          live_y_percent = (projected_hp_now / total_hp) * 100.0
          live_y_percent = max(0.0, min(100.0, live_y_percent))

          # Crosshairs lines
          ax.axhline(
              y=live_y_percent,
              color="#AEAEAE",
              linestyle="-",
              linewidth=0.8,
              alpha=0.7,
              zorder=1,
          )
          ax.axvline(
              x=live_x_hours,
              color="#AEAEAE",
              linestyle="-",
              linewidth=0.8,
              alpha=0.7,
              zorder=1,
          )

          # Translucent yellow dot
          ax.plot(
              live_x_hours,
              live_y_percent,
              "yo",
              markersize=8,
              alpha=STATIC_DOT_ALPHA,
              zorder=5,
          )

          update_performance_gauge(live_x_hours, live_y_percent)

    except Exception:
      pass

  # Optional Blue Staging Tracker
  if blue_tracker_var.get():
    ui_coords = get_current_ui_coordinates()
    if ui_coords and history:
      ui_x, ui_y, ui_dps, total_hp = ui_coords
      last_pt = history[-1]

      is_matching_x = abs(ui_x - last_pt[0]) < 0.001
      is_matching_y = abs(ui_y - last_pt[1]) < 0.001
      is_matching_dps = (
          abs(ui_dps - last_pt[2]) < 0.001 if len(last_pt) > 2 else True
      )

      if not (is_matching_x and is_matching_y and is_matching_dps):
        ax.plot(
            ui_x, ui_y, "bo", alpha=STATIC_DOT_ALPHA, markersize=8, zorder=4
        )
        if ui_dps > 0 and ui_y > 0:
          rem_hp_staging = (ui_y / 100.0) * total_hp
          h_to_kill_staging = (rem_hp_staging / ui_dps) / 3600.0
          staging_proj_x = ui_x + h_to_kill_staging
          ax.plot(
              [ui_x, staging_proj_x],
              [ui_y, 0],
              "b:",
              linewidth=1.5,
              alpha=0.6,
              zorder=2,
          )

        update_performance_gauge(ui_x, ui_y)

  ax.set_xlim(current_x_range[0], current_x_range[1])
  ax.set_ylim(current_y_range[0], current_y_range[1])
  canvas.draw_idle()


def start_tracking():
  global start_time, total_seconds_at_start, initial_hp_at_start, tracking_id, history
  if tracking_id:
    root.after_cancel(tracking_id)
  try:
    start_time = datetime.now()
    total_seconds_at_start = (
        (int(strip_non_numeric(days_entry.get())) * 86400)
        + (int(strip_non_numeric(hours_entry.get())) * 3600)
        + (int(strip_non_numeric(mins_entry.get())) * 60)
    )
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

    save_all()
    update_chart()
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
  global tracking_id, history
  try:
    tier_val = int(strip_non_numeric(tier_entry.get()))
    dps = float(strip_non_numeric(dps_entry.get()))
    elapsed = (datetime.now() - start_time).total_seconds()
    current_time_left = total_seconds_at_start - elapsed
    current_hp = initial_hp_at_start - (dps * elapsed)
    total_hp = TIER_DATA[tier_val]["health"]
    percent_left = (current_hp / total_hp) * 100.0

    # Auto-Update Day/Hour/Minute textboxes (+1 minute offset)
    if update_var.get() and current_time_left > 0:
      display_seconds = max(0, int(current_time_left) + 60)
      d_disp = display_seconds // 86400
      h_disp = (display_seconds % 86400) // 3600
      m_disp = (display_seconds % 3600) // 60

      block_trace_handlers(True)
      d_var.set(str(d_disp))
      h_var.set(str(h_disp))
      m_var.set(str(m_disp))
      block_trace_handlers(False)

    # Auto-Update Remaining HP textboxes with strict truncation (000 end) & comma formatting
    if update_hp_var.get() and current_hp > 0:
      rem_h = int(current_hp) // 1000000
      rem_h_sub_raw = int(current_hp) % 1000000
      rem_h_sub_truncated = (rem_h_sub_raw // 1000) * 1000

      block_trace_handlers(True)
      hp_var.set(f"{rem_h:,}")
      hp_sub_var.set(f"{rem_h_sub_truncated // 1000:03d},000")
      block_trace_handlers(False)

    projected_end_hp = current_hp - (dps * max(0, current_time_left))
    proj_percent = (
        (projected_end_hp / total_hp) * 100.0 if projected_end_hp > 0 else 0.0
    )

    draw_custom_progress_bar(percent_left, proj_percent)

    live_tracking_label.config(
        text=(
            f"Time left: {format_time_delta(current_time_left)}\nHP left:"
            f" {int(max(0, current_hp)):,}"
        )
    )

    tier_info = TIER_DATA[tier_val]
    tier_info_label.config(
        text=f'"{tier_info["name"]}" {tier_info["health"]:,.0f} HP'
    )

    update_day_indicator(current_time_left)

    if current_hp <= 0 or percent_left <= 0:
      status_label.config(text="TIAMAT DEFEATED!", fg="gold")
    else:
      if (dps * current_time_left) >= current_hp:
        success_time = (
            (dps * current_time_left - current_hp) / dps if dps > 0 else 0
        )
        status_label.config(
            text=(
                "On track to WIN!\nWin in:"
                f" {format_time_delta(current_time_left-success_time)}"
            ),
            fg="dark green",
        )
      else:
        delay = (
            (current_hp / dps) - current_time_left if dps > 0 else float("inf")
        )
        deficit = current_hp - (dps * current_time_left)
        needed_dps = deficit / current_time_left if current_time_left > 0 else 0
        status_label.config(
            text=(
                f"Projected to FAIL.\nNeed {needed_dps:,.0f} additional"
                f" DPS.\nLate by: {format_time_delta(delay)}"
            ),
            fg="red",
        )

    # Note: update_chart() removed from here to stop high CPU/lag every second
    tracking_id = root.after(1000, run_update)
  except:
    pass


def on_window_configure(event):
  """Throttles window movement/resize redrawing to keep window motion completely smooth."""
  global resize_timer_id
  if event.widget == root:
    if resize_timer_id is not None:
      root.after_cancel(resize_timer_id)
    resize_timer_id = root.after(100, _handle_throttled_resize)


def _handle_throttled_resize():
  global resize_timer_id
  resize_timer_id = None
  draw_custom_progress_bar(LAST_PROGRESS_PCTS[0], LAST_PROGRESS_PCTS[1])


def set_tier_defaults(tier_num=10):
  """Sets defaults for selected tier with formatted thousands separators."""
  try:
    t_val = int(tier_num)
    if t_val not in TIER_DATA:
      t_val = 10
  except:
    t_val = 10

  max_hp = TIER_DATA[t_val]["health"]
  hp_main = f"{int(max_hp) // 1000000:,}"
  hp_sub = "000,000"

  block_trace_handlers(True)
  tier_var.set(str(t_val))
  dps_var.set("0")
  hp_var.set(hp_main)
  hp_sub_var.set(hp_sub)
  d_var.set("6")
  h_var.set("23")
  m_var.set("60")
  block_trace_handlers(False)
  update_chart()


def on_tier_changed(*args):
  try:
    t_val = int(strip_non_numeric(tier_var.get()))
    if t_val in TIER_DATA:
      set_tier_defaults(t_val)
      return
  except:
    pass
  update_chart()


def load_all():
  global history, start_time, total_seconds_at_start, initial_hp_at_start
  has_active_run = False

  if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r") as f:
      try:
        data = json.load(f)
        block_trace_handlers(True)

        tier_entry.delete(0, tk.END)
        tier_entry.insert(0, data.get("tier", "10"))
        dps_entry.delete(0, tk.END)
        dps_entry.insert(0, data.get("dps", "0"))

        raw_hp_main = data.get("hp_main", "16,000")
        raw_hp_sub = data.get("hp_sub", "000,000")

        # Ensure commas on load
        clean_main = int(strip_non_numeric(raw_hp_main)) if raw_hp_main else 16000
        clean_sub = int(strip_non_numeric(raw_hp_sub)) if raw_hp_sub else 0

        health_entry.delete(0, tk.END)
        health_entry.insert(0, f"{clean_main:,}")
        health_suffix_entry.delete(0, tk.END)
        health_suffix_entry.insert(0, f"{(clean_sub // 1000) * 1000 // 1000:03d},000")

        days_entry.delete(0, tk.END)
        days_entry.insert(0, data.get("d", "6"))
        hours_entry.delete(0, tk.END)
        hours_entry.insert(0, data.get("h", "23"))
        mins_entry.delete(0, tk.END)
        mins_entry.insert(0, data.get("m", "60"))

        block_trace_handlers(False)

        saved_start = data.get("start_time")
        if saved_start:
          start_time = datetime.fromisoformat(saved_start)
          total_seconds_at_start = data.get("total_seconds_at_start", 0)
          initial_hp_at_start = data.get("initial_hp_at_start", 0)
          has_active_run = True
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

  if not has_active_run:
    set_tier_defaults(10)

  update_chart()
  if start_time:
    run_update()


def reload_chart():
  global CACHED_HISTORICAL_RUNS
  CACHED_HISTORICAL_RUNS = None
  load_all()
  messagebox.showinfo("Success", "Chart and data reloaded successfully.")


def reset_run():
  global history, start_time, total_seconds_at_start, initial_hp_at_start, tracking_id

  if tracking_id:
    root.after_cancel(tracking_id)
    tracking_id = None

  if messagebox.askyesno(
      "Confirm Reset",
      "Start a new run? This will clear active tracking for a new encounter.",
  ):
    history = []
    start_time = None
    total_seconds_at_start = 0
    initial_hp_at_start = 0

    status_label.config(text="", fg="black")
    draw_custom_progress_bar(100.0, 0.0)
    live_tracking_label.config(text="Time left: --\nHP left: --")

    set_tier_defaults(10)
    save_all()
    zoom_reset()
    update_chart()
    messagebox.showinfo(
        "Reset Complete",
        "Ready for a new run. Enter remaining time/HP and click Calculate!",
    )


def on_input_changed(*args):
  update_chart()


def block_trace_handlers(should_block):
  global tier_trace_id, dps_trace_id, hp_trace_id, hp_sub_trace_id, d_trace_id, h_trace_id, m_trace_id

  if should_block:
    tier_var.trace_remove("write", tier_trace_id)
    dps_var.trace_remove("write", dps_trace_id)
    hp_var.trace_remove("write", hp_trace_id)
    hp_sub_trace_id = hp_sub_var.trace_remove("write", hp_sub_trace_id)
    d_var.trace_remove("write", d_trace_id)
    h_var.trace_remove("write", h_trace_id)
    m_var.trace_remove("write", m_trace_id)
  else:
    tier_trace_id = tier_var.trace_add("write", on_tier_changed)
    dps_trace_id = dps_var.trace_add("write", on_input_changed)
    hp_trace_id = hp_var.trace_add("write", on_input_changed)
    hp_sub_trace_id = hp_sub_var.trace_add("write", on_input_changed)
    d_trace_id = d_var.trace_add("write", on_input_changed)
    h_trace_id = h_var.trace_add("write", on_input_changed)
    m_trace_id = m_var.trace_add("write", on_input_changed)


# --- GUI SETUP ---
root = tk.Tk()
root.title("ToMT Tier Progress Calculator")
root.geometry("600x670")
root.minsize(500, 550)

# Window configure listener for smooth dragging
root.bind("<Configure>", on_window_configure)

# Main Controls Layout Container
input_frame = tk.Frame(root)
input_frame.grid(row=0, column=0, columnspan=4, pady=(10, 5))

tier_var = tk.StringVar(value="10")
dps_var = tk.StringVar(value="0")
hp_var = tk.StringVar(value="16,000")
hp_sub_var = tk.StringVar(value="000,000")
d_var = tk.StringVar(value="6")
h_var = tk.StringVar(value="23")
m_var = tk.StringVar(value="60")

update_hp_var = tk.BooleanVar(value=True)
update_var = tk.BooleanVar(value=True)
blue_tracker_var = tk.BooleanVar(value=False)

# Row 0: Tier & Total DPS
tk.Label(input_frame, text="Tier (1-10):").grid(
    row=0, column=0, sticky="e", padx=(0, 2)
)
tier_entry = tk.Entry(input_frame, width=8, textvariable=tier_var)
tier_entry.grid(row=0, column=1, sticky="w", padx=(0, 15))

tk.Label(input_frame, text="Total DPS:").grid(
    row=0, column=2, sticky="e", padx=(0, 2)
)
dps_entry = tk.Entry(input_frame, width=12, textvariable=dps_var)
dps_entry.grid(row=0, column=3, sticky="w")

# Row 1: Remaining HP Main, Suffix, & Top Update Checkbox
tk.Label(input_frame, text="Remaining HP:").grid(
    row=1, column=0, sticky="e", padx=(0, 2), pady=3
)
health_entry = tk.Entry(input_frame, width=8, textvariable=hp_var)
health_entry.grid(row=1, column=1, sticky="w", padx=(0, 15), pady=3)

health_suffix_entry = tk.Entry(input_frame, width=8, textvariable=hp_sub_var)
health_suffix_entry.grid(row=1, column=2, sticky="w", pady=3)

update_hp_cb = tk.Checkbutton(
    input_frame,
    text="Update",
    variable=update_hp_var,
    font=("Arial", 9, "bold"),
)
update_hp_cb.grid(row=1, column=3, sticky="w", padx=(10, 0), pady=3)

# Row 2: Duration Controls & Bottom Update Checkbox
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

update_cb = tk.Checkbutton(
    time_frame, text="Update", variable=update_var, font=("Arial", 9, "bold")
)
update_cb.pack(side=tk.LEFT, padx=(10, 0))

# Performance Gauge Bar
gauge_frame = tk.Frame(root)
gauge_frame.place(relx=0.88, y=10, anchor="n")

gauge_canvas = tk.Canvas(
    gauge_frame, width=30, height=110, highlightthickness=0
)
gauge_canvas.pack(side=tk.TOP)

gauge_label = tk.Label(gauge_frame, text="--", font=("Arial", 9, "bold"))
gauge_label.pack(side=tk.TOP, pady=(4, 0))

# Bind Trace Handlers
tier_trace_id = tier_var.trace_add("write", on_tier_changed)
dps_trace_id = dps_var.trace_add("write", on_input_changed)
hp_trace_id = hp_var.trace_add("write", on_input_changed)
hp_sub_trace_id = hp_sub_var.trace_add("write", on_input_changed)
d_trace_id = d_var.trace_add("write", on_input_changed)
h_trace_id = h_var.trace_add("write", on_input_changed)
m_trace_id = m_var.trace_add("write", on_input_changed)

# Action Buttons
button_frame = tk.Frame(root)
button_frame.grid(row=1, column=0, columnspan=4, pady=5)
tk.Button(
    button_frame, text="Calculate", command=start_tracking, width=12
).pack(side=tk.LEFT, padx=3)
tk.Button(
    button_frame, text="New Run", command=reset_run, width=12, fg="blue"
).pack(side=tk.LEFT, padx=3)
tk.Button(
    button_frame, text="ReLoad Chart", command=reload_chart, width=12, fg="red"
).pack(side=tk.LEFT, padx=3)

# Live Tracking Display & Day Indicator
tracking_container = tk.Frame(root)
tracking_container.grid(row=2, column=0, columnspan=4, pady=5)

live_tracking_label = tk.Label(
    tracking_container,
    text="Time left: --\nHP left: --",
    font=("Arial", 10),
    bg="lightyellow",
    highlightthickness=1,
)
live_tracking_label.pack(side=tk.LEFT, padx=5)

day_canvas = tk.Canvas(
    tracking_container, width=24, height=24, highlightthickness=0
)
day_canvas.pack(side=tk.LEFT, padx=5)
day_circle_id = day_canvas.create_oval(
    3, 3, 21, 21, fill="green", outline="black"
)
day_canvas.bind("<Button-1>", on_day_indicator_click)

# Status & Info Labels
tier_info_label = tk.Label(root, text="", font=("Arial", 10, "bold"))
tier_info_label.grid(row=3, column=0, columnspan=4)

status_label = tk.Label(
    root, text="", font=("Arial", 10, "bold"), justify="center"
)
status_label.grid(row=4, column=0, columnspan=4)

# Options & Zoom Controls Row
zoom_frame = tk.Frame(root)
zoom_frame.grid(row=5, column=0, columnspan=4, sticky="ew", padx=15, pady=(2, 0))

blue_tracker_cb = tk.Checkbutton(
    zoom_frame,
    text="blue tracker",
    variable=blue_tracker_var,
    command=update_chart,
    font=("Arial", 9, "bold"),
)
blue_tracker_cb.pack(side=tk.LEFT)

zoom_controls_inner = tk.Frame(zoom_frame)
zoom_controls_inner.pack(side=tk.RIGHT)

tk.Label(
    zoom_controls_inner, text="Zoom:", font=("Arial", 8, "bold")
).pack(side=tk.LEFT, padx=(0, 3))
tk.Button(
    zoom_controls_inner,
    text=" - ",
    command=zoom_out,
    width=3,
    font=("Arial", 8, "bold"),
).pack(side=tk.LEFT, padx=1)
tk.Button(
    zoom_controls_inner,
    text=" + ",
    command=zoom_in,
    width=3,
    font=("Arial", 8, "bold"),
).pack(side=tk.LEFT, padx=1)
tk.Button(
    zoom_controls_inner, text=" Reset ", command=zoom_reset, font=("Arial", 8)
).pack(side=tk.LEFT, padx=(2, 0))

# Matplotlib Chart
root.rowconfigure(6, weight=1)
root.columnconfigure(0, weight=1)

fig = plt.Figure(figsize=(5, 3), dpi=100)
ax = fig.add_subplot(111)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(
    row=6, column=0, columnspan=4, sticky="nsew", padx=10, pady=5
)

# Custom Progress Bar Canvas Layout Container
progress_container = tk.Frame(root, bg="white")
progress_container.grid(
    row=7, column=0, columnspan=4, sticky="ew", pady=7, padx=10
)

progress_canvas = tk.Canvas(
    progress_container, height=30, bg="black", highlightthickness=0
)
progress_canvas.pack(fill="x", expand=True)

draw_gauge_gradient()
load_all()
root.mainloop()