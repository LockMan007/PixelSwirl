import pyvista as pv
import numpy as np
import struct

# =========================
# FF7 MODEL LOADER
# =========================

def load_ff7_model(filename):
    with open(filename, 'rb') as f:
        data = bytearray(f.read())

        num_v = struct.unpack('<I', data[12:16])[0]
        num_n = struct.unpack('<I', data[16:20])[0]
        num_t = struct.unpack('<I', data[24:28])[0]
        num_c = struct.unpack('<I', data[28:32])[0]

        vertex_start = 128
        verts = np.frombuffer(
            data[vertex_start : vertex_start + (num_v * 12)],
            dtype=np.float32
        ).reshape(-1, 3)

        offset = 128 + (num_v * 12) + (num_n * 24) + (num_t * 8)
        color_raw = data[offset : offset + (num_c * 4)]
        color_data = np.frombuffer(color_raw, dtype=np.uint8).reshape(-1, 4)

        rgb = color_data[:, [2, 1, 0]].copy()

    return verts, rgb, data, offset, num_c


# =========================
# GLOBAL STATE
# =========================

FILE_NAME = "ruam"

verts, current_rgb, full_raw_data, color_offset, color_count = load_ff7_model(FILE_NAME)

original_rgb = current_rgb.copy()
modified_mask = np.zeros(color_count, dtype=bool)

colors = [
    np.array([156, 114, 102], dtype=np.int16),
    np.array([200, 150, 120], dtype=np.int16)
]

active_slot = 0
restrict_changes = True

point_size_val = 100.0
surface_smooth = True
render_mode = "points"  # points | surface

plotter = pv.Plotter(window_size=[1100, 800])
plotter.background_color = "white"

cloud = pv.PolyData(verts)
cloud["colors"] = current_rgb

actor_name = "model"

# Pre-calculate geometry using your "x" file logic
_volume = cloud.delaunay_3d(alpha=0.0)
base_surface = _volume.extract_surface(algorithm="dataset_surface")


# =========================
# RENDER SYSTEM
# =========================

def refresh_mesh():
    plotter.remove_actor(actor_name)

    # Keep points synced
    cloud["colors"] = current_rgb

    if render_mode == "points":
        plotter.add_mesh(
            cloud,
            scalars="colors",
            rgb=True,
            render_points_as_spheres=True,
            point_size=point_size_val,
            name=actor_name
        )
    else:
        # Transfer colors from the 243 points to the 66 surface points
        updated_surface = base_surface.sample(cloud)
        
        plotter.add_mesh(
            updated_surface,
            scalars="colors",
            rgb=True,
            smooth_shading=surface_smooth,
            name=actor_name
        )

    update_mode_label()


def toggle_render_mode(state=None):
    global render_mode
    render_mode = "surface" if render_mode == "points" else "points"
    refresh_mesh()


def toggle_smooth(state):
    global surface_smooth
    surface_smooth = state
    if render_mode == "surface":
        refresh_mesh()


def update_mode_label():
    plotter.add_text(
        f"MODE: {render_mode.upper()}",
        position=(850, 760),
        font_size=12,
        color="black",
        name="mode_label"
    )


# =========================
# COLOR UI
# =========================

def update_color_displays():
    gui_x = 20
    labels = ["R", "G", "B"]

    for i in range(2):
        y_offset = 740 if i == 0 else 600
        for c in range(3):
            y = y_offset - (c * 25)
            plotter.add_text(
                f"{labels[c]}: {colors[i][c]}",
                position=(gui_x, y),
                font_size=9,
                color="black",
                name=f"txt_{i}_{c}"
            )

        border = "yellow" if active_slot == i else "black"
        plotter.add_checkbox_button_widget(
            lambda b, idx=i: set_active_selection(idx),
            value=True,
            position=(135, y_offset - 45),
            size=65,
            color_on=colors[i].astype(float)/255.0,
            color_off=colors[i].astype(float)/255.0,
            background_color=border
        )


def adjust_rgb(slot, channel, delta):
    colors[slot][channel] = np.clip(colors[slot][channel] + delta, 0, 255)
    update_color_displays()


def set_active_selection(slot):
    global active_slot
    active_slot = slot
    update_color_displays()


# =========================
# ACTIONS
# =========================

def apply_tint_all(state=None):
    global current_rgb
    tint = colors[active_slot].astype(float) / 255.0
    for i in range(color_count):
        if restrict_changes and modified_mask[i]:
            continue
        current_rgb[i] = np.clip(original_rgb[i] * tint, 0, 255).astype(np.uint8)
        modified_mask[i] = True
    refresh_mesh()


def adjust_brightness(factor):
    indices = np.where(modified_mask)[0]
    for i in indices:
        current_rgb[i] = np.clip(current_rgb[i].astype(float) * factor, 0, 255).astype(np.uint8)
    refresh_mesh()


def toggle_restriction(state):
    global restrict_changes
    restrict_changes = state


def update_point_size(value):
    global point_size_val
    point_size_val = value
    if render_mode == "points":
        refresh_mesh()


def save_model(state=None):
    for i in range(color_count):
        pos = color_offset + (i * 4)
        full_raw_data[pos]     = int(current_rgb[i, 2])
        full_raw_data[pos + 1] = int(current_rgb[i, 1])
        full_raw_data[pos + 2] = int(current_rgb[i, 0])
        full_raw_data[pos + 3] = 255
    with open(f"{FILE_NAME}_modified.p", "wb") as f:
        f.write(full_raw_data)
    print("Export successful.")


# =========================
# INTERACTION
# =========================

def on_click(*args):
    if not args or args[0] is None:
        return
    point = args[0]
    idx = cloud.find_closest_point(point)
    if restrict_changes and modified_mask[idx]:
        return
    tint = colors[active_slot].astype(float) / 255.0
    current_rgb[idx] = np.clip(original_rgb[idx] * tint, 0, 255).astype(np.uint8)
    modified_mask[idx] = True
    refresh_mesh()


# =========================
# UI BUILDER
# =========================

def build_static_ui():
    gui_x = 20
    for i in range(2):
        y_offset = 740 if i == 0 else 600
        for channel in range(3):
            y = y_offset - (channel * 25)
            plotter.add_checkbox_button_widget(
                lambda b, s=i, c=channel: adjust_rgb(s, c, 5),
                position=(gui_x + 65, y), size=18,
                color_on="white", color_off="white", background_color="white"
            )
            plotter.add_text("+", position=(gui_x + 68, y + 2), font_size=8, color="black")
            plotter.add_checkbox_button_widget(
                lambda b, s=i, c=channel: adjust_rgb(s, c, -5),
                position=(gui_x + 85, y), size=18,
                color_on="white", color_off="white", background_color="white"
            )
            plotter.add_text("-", position=(gui_x + 89, y + 2), font_size=8, color="black")

    y_base = 380
    plotter.add_checkbox_button_widget(lambda b: apply_tint_all(), position=(gui_x, y_base), size=40)
    plotter.add_text("Tint ALL", position=(gui_x + 50, y_base), color="black")
    plotter.add_checkbox_button_widget(lambda state: adjust_brightness(1.1), position=(gui_x, y_base - 60), size=40)
    plotter.add_text("Lighten All", position=(gui_x + 50, y_base - 60), color="black")
    plotter.add_checkbox_button_widget(lambda state: adjust_brightness(0.9), position=(gui_x, y_base - 130), size=40)
    plotter.add_text("Darken All", position=(gui_x + 50, y_base - 130), color="black")
    plotter.add_checkbox_button_widget(lambda b: save_model(), position=(gui_x, y_base - 180), size=40)
    plotter.add_text("Save", position=(gui_x + 50, y_base - 180), color="black")
    plotter.add_checkbox_button_widget(toggle_render_mode, position=(gui_x, y_base - 230), size=40)
    plotter.add_text("Toggle Render Mode", position=(gui_x + 50, y_base - 230), color="black")
    plotter.add_checkbox_button_widget(toggle_smooth, value=True, position=(gui_x, y_base - 280), size=40)
    plotter.add_text("Smooth Surface", position=(gui_x + 50, y_base - 280), color="black")
    plotter.add_checkbox_button_widget(toggle_restriction, value=restrict_changes, position=(gui_x, y_base - 340), size=30)
    plotter.add_text("Restrict to 1 change", position=(gui_x + 40, y_base - 340), color="black")
    plotter.add_slider_widget(update_point_size, [1, 250], value=100,
                              title="Point Size",
                              pointa=(0.6, 0.12), pointb=(0.9, 0.12), color="black")

# =========================
# RUN
# =========================

refresh_mesh()
build_static_ui()
update_color_displays()
plotter.enable_point_picking(callback=on_click, show_message=False, color="yellow")
plotter.show()