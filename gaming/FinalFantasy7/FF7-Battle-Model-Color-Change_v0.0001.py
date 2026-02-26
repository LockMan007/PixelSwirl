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

# Target Peach/Skin tones
colors = [
    np.array([156, 114, 102], dtype=np.uint8),
    np.array([200, 150, 120], dtype=np.uint8)
]
active_slot = 0
restrict_changes = True
point_size_val = 100.0

# --- PyVista Setup ---
plotter = pv.Plotter(window_size=[1100, 800])
cloud = pv.PolyData(verts)
cloud['colors'] = current_rgb
plotter.background_color = "white"

def refresh_mesh():
    cloud['colors'] = current_rgb
    plotter.add_mesh(cloud, scalars='colors', rgb=True, render_points_as_spheres=True, 
                     point_size=point_size_val, name="model")

def set_active(slot):
    global active_slot
    active_slot = slot
    draw_ui()

def draw_ui():
    """Builds the left-side control panel using fixed offsets."""
    gui_x = 20 
    
    # Slot 1
    b1 = "yellow" if active_slot == 0 else "black"
    plotter.add_text(f"{colors[0][0]} {colors[0][1]} {colors[0][2]}", position=(gui_x, 740), font_size=10, color="black", name="t1")
    plotter.add_checkbox_button_widget(lambda b: set_active(0), value=True, position=(gui_x, 670), size=60, 
                                       color_on=colors[0]/255.0, color_off=colors[0]/255.0, background_color=b1)
    
    # Slot 2
    b2 = "yellow" if active_slot == 1 else "black"
    plotter.add_text(f"{colors[1][0]} {colors[1][1]} {colors[1][2]}", position=(gui_x, 600), font_size=10, color="black", name="t2")
    plotter.add_checkbox_button_widget(lambda b: set_active(1), value=True, position=(gui_x, 530), size=60, 
                                       color_on=colors[1]/255.0, color_off=colors[1]/255.0, background_color=b2)

    # Point Size Readout
    plotter.add_text(f"Point Size: {int(point_size_val)}", position=(gui_x, 480), font_size=10, color="black", name="sz_lbl")

    # Action Buttons (Column)
    y_base = 380
    plotter.add_checkbox_button_widget(lambda b: apply_tint_all(), position=(gui_x, y_base), size=40, color_on="lightgrey")
    plotter.add_text("Tint ALL", position=(gui_x + 50, y_base + 10), font_size=10, color="black", name="btn_tint")

    plotter.add_checkbox_button_widget(lambda b: adjust_brightness(1.1), position=(gui_x, y_base - 70), size=40, color_on="lightgrey")
    plotter.add_text("Lighten All", position=(gui_x + 50, y_base - 60), font_size=10, color="black", name="btn_light")

    plotter.add_checkbox_button_widget(lambda b: adjust_brightness(0.9), position=(gui_x, y_base - 140), size=40, color_on="lightgrey")
    plotter.add_text("Darken All", position=(gui_x + 50, y_base - 130), font_size=10, color="black", name="btn_dark")

    plotter.add_checkbox_button_widget(lambda b: save_model(), position=(gui_x, y_base - 210), size=40, color_on="lightgrey")
    plotter.add_text("Save", position=(gui_x + 50, y_base - 200), font_size=10, color="black", name="btn_save")

    # Logic Toggle
    plotter.add_checkbox_button_widget(toggle_restriction, value=restrict_changes, position=(gui_x, 50), size=30)
    plotter.add_text("restrict to 1 change each", position=(gui_x + 40, 55), font_size=9, color="black", name="btn_restr")

# --- Logic Actions ---

def apply_tint_all():
    global current_rgb
    tint = colors[active_slot] / 255.0
    for i in range(color_count):
        if restrict_changes and modified_mask[i]: continue
        current_rgb[i] = np.clip(original_rgb[i] * tint, 0, 255).astype(np.uint8)
        modified_mask[i] = True
    refresh_mesh()

def adjust_brightness(factor):
    global current_rgb
    # Modifies only the dots that have already been tinted
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
    draw_ui() 

def save_model():
    for i in range(color_count):
        pos = color_offset + (i * 4)
        full_raw_data[pos:pos+3] = current_rgb[i, [2, 1, 0]]
        full_raw_data[pos+3] = 255
    with open(f'{FILE_NAME}_shaded.p', 'wb') as f:
        f.write(full_raw_data)
    print(f"Export successful: {FILE_NAME}_shaded.p")

def on_click(point):
    idx = cloud.find_closest_point(point)
    if restrict_changes and modified_mask[idx]: return
    tint = colors[active_slot] / 255.0
    current_rgb[idx] = np.clip(original_rgb[idx] * tint, 0, 255).astype(np.uint8)
    modified_mask[idx] = True
    refresh_mesh()

# --- Execution ---
refresh_mesh()
draw_ui()

# Slider positioned in the bottom right corner (normalized coords)
plotter.add_slider_widget(update_point_size, [1, 250], value=100, title="", 
                          pointa=(0.6, 0.05), pointb=(0.9, 0.05))

plotter.enable_point_picking(callback=on_click, show_message=False, color='yellow')
plotter.show()