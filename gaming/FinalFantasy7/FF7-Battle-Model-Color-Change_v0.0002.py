import pyvista as pv
import numpy as np
import struct

def load_ff7_model(filename):
    with open(filename, 'rb') as f:
        data = bytearray(f.read())
        num_v = struct.unpack('<I', data[12:16])[0]
        num_n = struct.unpack('<I', data[16:20])[0]
        num_t = struct.unpack('<I', data[24:28])[0]
        num_c = struct.unpack('<I', data[28:32])[0]
        
        vertex_start = 128
        verts = np.frombuffer(data[vertex_start : vertex_start + (num_v * 12)], dtype=np.float32).reshape(-1, 3)
        
        offset = 128 + (num_v * 12) + (num_n * 24) + (num_t * 8)
        color_raw = data[offset : offset + (num_c * 4)]
        color_data = np.frombuffer(color_raw, dtype=np.uint8).reshape(-1, 4)
        rgb = color_data[:, [2, 1, 0]].copy()
        
    return verts, rgb, data, offset, num_c

# --- Global State ---
FILE_NAME = 'ruam'
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

plotter = pv.Plotter(window_size=[1100, 800])
cloud = pv.PolyData(verts)
cloud['colors'] = current_rgb
plotter.background_color = "white"

def refresh_mesh():
    cloud['colors'] = current_rgb
    plotter.add_mesh(cloud, scalars='colors', rgb=True, render_points_as_spheres=True, 
                     point_size=point_size_val, name="model")

# --- Dynamic UI Updates ---

def update_color_displays():
    """Updates the numeric labels and the color box color."""
    gui_x = 20
    labels = ["R", "G", "B"]
    
    for i in range(2):
        y_offset = 740 if i == 0 else 600
        # Update Text Labels (using 'name' ensures it replaces the old text instantly)
        for c in range(3):
            y = y_offset - (c * 25)
            plotter.add_text(f"{labels[c]}: {colors[i][c]}", position=(gui_x, y), 
                             font_size=9, color="black", name=f"txt_{i}_{c}")
        
        # Update the Large Color Box
        # We recreate the widget only when the color changes to avoid stacking
        border = "yellow" if active_slot == i else "black"
        plotter.add_checkbox_button_widget(
            lambda b, idx=i: set_active_selection(idx), 
            value=True, position=(135, y_offset - 45), size=65, 
            color_on=colors[i].astype(float)/255.0, 
            color_off=colors[i].astype(float)/255.0, 
            background_color=border
        )

def adjust_rgb(slot, channel, delta):
    """Adjusts values and updates only what is necessary (Instant)."""
    colors[slot][channel] = np.clip(colors[slot][channel] + delta, 0, 255)
    update_color_displays()

def set_active_selection(slot):
    global active_slot
    active_slot = slot
    update_color_displays()

# --- Initial UI Construction (Run ONCE) ---

def build_static_ui():
    gui_x = 20
    # 1. Create adjustment buttons once
    for i in range(2):
        y_offset = 740 if i == 0 else 600
        for channel in range(3):
            y = y_offset - (channel * 25)
            
            # Plus (White background to hide gray box)
            plotter.add_checkbox_button_widget(lambda b, s=i, c=channel: adjust_rgb(s, c, 5),
                position=(gui_x + 65, y), size=18, color_on="white", color_off="white", background_color="white")
            plotter.add_text("+", position=(gui_x + 68, y + 2), font_size=8, color="black")

            # Minus
            plotter.add_checkbox_button_widget(lambda b, s=i, c=channel: adjust_rgb(s, c, -5),
                position=(gui_x + 85, y), size=18, color_on="white", color_off="white", background_color="white")
            plotter.add_text("-", position=(gui_x + 89, y + 2), font_size=8, color="black")

    # 2. Create Action Buttons once
    y_base = 380
    # Tint All
    plotter.add_checkbox_button_widget(lambda b: apply_tint_all(), position=(gui_x, y_base), size=40, color_on="lightgrey")
    plotter.add_text("Tint ALL", position=(gui_x + 50, y_base + 10), font_size=10, color="black")
    # Lighten
    plotter.add_checkbox_button_widget(lambda b: adjust_brightness(1.1), position=(gui_x, y_base - 70), size=40, color_on="lightgrey")
    plotter.add_text("Lighten All", position=(gui_x + 50, y_base - 60), font_size=10, color="black")
    # Darken (Restored)
    plotter.add_checkbox_button_widget(lambda b: adjust_brightness(0.9), position=(gui_x, y_base - 140), size=40, color_on="lightgrey")
    plotter.add_text("Darken All", position=(gui_x + 50, y_base - 130), font_size=10, color="black")
    # Save
    plotter.add_checkbox_button_widget(lambda b: save_model(), position=(gui_x, y_base - 210), size=40, color_on="lightgrey")
    plotter.add_text("Save", position=(gui_x + 50, y_base - 200), font_size=10, color="black")

    # 3. Restriction Toggle
    plotter.add_checkbox_button_widget(toggle_restriction, value=restrict_changes, position=(gui_x, 50), size=30)
    plotter.add_text("restrict to 1 change each", position=(gui_x + 40, 55), font_size=9, color="black")

    # 4. Point Size Slider
    plotter.add_slider_widget(update_point_size, [1, 250], value=100, title="", 
                              pointa=(0.6, 0.05), pointb=(0.9, 0.05))

# --- Logic Actions ---

def apply_tint_all():
    global current_rgb
    tint = colors[active_slot].astype(float) / 255.0
    for i in range(color_count):
        if restrict_changes and modified_mask[i]: continue
        current_rgb[i] = np.clip(original_rgb[i] * tint, 0, 255).astype(np.uint8)
        modified_mask[i] = True
    refresh_mesh()

def adjust_brightness(factor):
    global current_rgb
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
    refresh_mesh()

def save_model():
    for i in range(color_count):
        pos = color_offset + (i * 4)
        full_raw_data[pos:pos+3] = current_rgb[i, [2, 1, 0]]
        full_raw_data[pos+3] = 255
    with open(f'{FILE_NAME}_shaded.p', 'wb') as f:
        f.write(full_raw_data)
    print("Export successful.")

def on_click(point):
    idx = cloud.find_closest_point(point)
    if restrict_changes and modified_mask[idx]: return
    tint = colors[active_slot].astype(float) / 255.0
    current_rgb[idx] = np.clip(original_rgb[idx] * tint, 0, 255).astype(np.uint8)
    modified_mask[idx] = True
    refresh_mesh()

# --- Execution ---
refresh_mesh()
build_static_ui()
update_color_displays() # Build initial dynamic labels
plotter.enable_point_picking(callback=on_click, show_message=False, color='yellow')
plotter.show()