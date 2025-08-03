import sounddevice as sd
import numpy as np
from scipy.fftpack import fft
from scipy.signal import spectrogram
import pygame
import configparser
import os
import sys
import ctypes
from ctypes import wintypes
import collections

# --- Configuration ---
CHUNK_SIZE = 1024
SAMPLING_RATE = 48000
DEVICE_ID = 22

# --- Settings File ---
SETTINGS_FILE = 'settings.ini'
config = configparser.ConfigParser()

# --- Global Variables for Application State ---
APP_STATE_MAIN = "main"
APP_STATE_SETTINGS = "settings"
app_state = APP_STATE_MAIN

# --- Global Variables for Settings ---
GAIN_FACTOR = 5.0
OSCILLOSCOPE_ACTIVE = True
SPECTRUM_ACTIVE = True
SPECTROGRAM_ACTIVE = True
TARGET_BAR_COUNT = 60

BACKGROUND_COLOR = (0, 0, 0)
OSCILLOSCOPE_COLORS = [(0, 0, 255)] # Default to blue
OSCILLOSCOPE_COLOR_COUNT = 1
OSCILLOSCOPE_GRADIENT_ACTIVE = False

SPECTRUM_COLORS = [(0, 255, 0)] # Default to green
SPECTRUM_COLOR_COUNT = 1
SPECTRUM_GRADIENT_ACTIVE = False

SPECTROGRAM_COLORS = [(255, 0, 0)] # Default to red
SPECTROGRAM_COLOR_COUNT = 1
SPECTROGRAM_GRADIENT_ACTIVE = False
SPECTROGRAM_BUFFER_SIZE = 200 # Number of spectrogram columns to store

# --- Global Variables for Window State ---
INITIAL_SCREEN_WIDTH = 800
INITIAL_SCREEN_HEIGHT = 400
last_window_width = INITIAL_SCREEN_WIDTH
last_window_height = INITIAL_SCREEN_HEIGHT
last_window_x = 100
last_window_y = 100
is_fullscreen = False
screen_size = (INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT)

# --- Spectrogram Buffer ---
spectrogram_buffer = collections.deque(maxlen=SPECTROGRAM_BUFFER_SIZE)

# --- Load Settings ---
def load_settings():
    global GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, BACKGROUND_COLOR, \
           OSCILLOSCOPE_COLORS, OSCILLOSCOPE_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, \
           SPECTRUM_COLORS, SPECTRUM_COLOR_COUNT, SPECTRUM_GRADIENT_ACTIVE, \
           SPECTROGRAM_COLORS, SPECTROGRAM_COLOR_COUNT, SPECTROGRAM_GRADIENT_ACTIVE

    if os.path.exists(SETTINGS_FILE):
        try:
            config.read(SETTINGS_FILE)
            if 'SpectrumAnalyzer' in config:
                GAIN_FACTOR = float(config['SpectrumAnalyzer'].get('gain_factor', GAIN_FACTOR))
                OSCILLOSCOPE_ACTIVE = config['SpectrumAnalyzer'].getboolean('oscilloscope_active', OSCILLOSCOPE_ACTIVE)
                SPECTRUM_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrum_active', SPECTRUM_ACTIVE)
                SPECTROGRAM_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrogram_active', SPECTROGRAM_ACTIVE)
                BACKGROUND_COLOR = eval(config['SpectrumAnalyzer'].get('background_color', str(BACKGROUND_COLOR)))
                
                OSCILLOSCOPE_COLOR_COUNT = int(config['SpectrumAnalyzer'].get('oscilloscope_color_count', OSCILLOSCOPE_COLOR_COUNT))
                OSCILLOSCOPE_GRADIENT_ACTIVE = config['SpectrumAnalyzer'].getboolean('oscilloscope_gradient_active', OSCILLOSCOPE_GRADIENT_ACTIVE)
                OSCILLOSCOPE_COLORS = [eval(config['SpectrumAnalyzer'][f'oscilloscope_color_{i+1}']) for i in range(OSCILLOSCOPE_COLOR_COUNT)]
                
                SPECTRUM_COLOR_COUNT = int(config['SpectrumAnalyzer'].get('spectrum_color_count', SPECTRUM_COLOR_COUNT))
                SPECTRUM_GRADIENT_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrum_gradient_active', SPECTRUM_GRADIENT_ACTIVE)
                SPECTRUM_COLORS = [eval(config['SpectrumAnalyzer'][f'spectrum_color_{i+1}']) for i in range(SPECTRUM_COLOR_COUNT)]

                SPECTROGRAM_COLOR_COUNT = int(config['SpectrumAnalyzer'].get('spectrogram_color_count', SPECTROGRAM_COLOR_COUNT))
                SPECTROGRAM_GRADIENT_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrogram_gradient_active', SPECTROGRAM_GRADIENT_ACTIVE)
                SPECTROGRAM_COLORS = [eval(config['SpectrumAnalyzer'][f'spectrogram_color_{i+1}']) for i in range(SPECTROGRAM_COLOR_COUNT)]

                print(f"Settings loaded from {SETTINGS_FILE}.")
            else:
                print(f"Warning: [SpectrumAnalyzer] section not found in {SETTINGS_FILE}. Using defaults.")
                reset_default_settings()
        except Exception as e:
            print(f"Error reading {SETTINGS_FILE}: {e}. Using default settings.", file=sys.stderr)
            reset_default_settings()
    else:
        print(f"Info: {SETTINGS_FILE} not found. Creating with default settings.")
        reset_default_settings()
    save_settings()

# --- Save Settings ---
def save_settings():
    if 'SpectrumAnalyzer' not in config:
        config['SpectrumAnalyzer'] = {}
    config['SpectrumAnalyzer']['gain_factor'] = str(GAIN_FACTOR)
    config['SpectrumAnalyzer']['oscilloscope_active'] = str(OSCILLOSCOPE_ACTIVE)
    config['SpectrumAnalyzer']['spectrum_active'] = str(SPECTRUM_ACTIVE)
    config['SpectrumAnalyzer']['spectrogram_active'] = str(SPECTROGRAM_ACTIVE)
    config['SpectrumAnalyzer']['background_color'] = str(BACKGROUND_COLOR)
    
    config['SpectrumAnalyzer']['oscilloscope_color_count'] = str(OSCILLOSCOPE_COLOR_COUNT)
    config['SpectrumAnalyzer']['oscilloscope_gradient_active'] = str(OSCILLOSCOPE_GRADIENT_ACTIVE)
    for i, color in enumerate(OSCILLOSCOPE_COLORS):
        config['SpectrumAnalyzer'][f'oscilloscope_color_{i+1}'] = str(color)
        
    config['SpectrumAnalyzer']['spectrum_color_count'] = str(SPECTRUM_COLOR_COUNT)
    config['SpectrumAnalyzer']['spectrum_gradient_active'] = str(SPECTRUM_GRADIENT_ACTIVE)
    for i, color in enumerate(SPECTRUM_COLORS):
        config['SpectrumAnalyzer'][f'spectrum_color_{i+1}'] = str(color)

    config['SpectrumAnalyzer']['spectrogram_color_count'] = str(SPECTROGRAM_COLOR_COUNT)
    config['SpectrumAnalyzer']['spectrogram_gradient_active'] = str(SPECTROGRAM_GRADIENT_ACTIVE)
    for i, color in enumerate(SPECTROGRAM_COLORS):
        config['SpectrumAnalyzer'][f'spectrogram_color_{i+1}'] = str(color)

    try:
        with open(SETTINGS_FILE, 'w') as configfile:
            config.write(configfile)
        print(f"Settings saved to {SETTINGS_FILE}.")
    except Exception as e:
        print(f"Error saving {SETTINGS_FILE}: {e}", file=sys.stderr)

# --- Reset Default Settings ---
def reset_default_settings():
    global GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, BACKGROUND_COLOR, \
           OSCILLOSCOPE_COLORS, OSCILLOSCOPE_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, \
           SPECTRUM_COLORS, SPECTRUM_COLOR_COUNT, SPECTRUM_GRADIENT_ACTIVE, \
           SPECTROGRAM_COLORS, SPECTROGRAM_COLOR_COUNT, SPECTROGRAM_GRADIENT_ACTIVE
    GAIN_FACTOR = 5.0
    OSCILLOSCOPE_ACTIVE = True
    SPECTRUM_ACTIVE = True
    SPECTROGRAM_ACTIVE = True
    BACKGROUND_COLOR = (0, 0, 0)
    OSCILLOSCOPE_COLORS = [(0, 0, 255)]
    OSCILLOSCOPE_COLOR_COUNT = 1
    OSCILLOSCOPE_GRADIENT_ACTIVE = False
    SPECTRUM_COLORS = [(0, 255, 0)]
    SPECTRUM_COLOR_COUNT = 1
    SPECTRUM_GRADIENT_ACTIVE = False
    SPECTROGRAM_COLORS = [(255, 0, 0)]
    SPECTROGRAM_COLOR_COUNT = 1
    SPECTROGRAM_GRADIENT_ACTIVE = False

# Initial call to load settings or set defaults
reset_default_settings()
load_settings()

# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode((INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Spectrum Analyzer")
clock = pygame.time.Clock()

# --- ctypes for window positioning on Windows ---
if sys.platform == "win32":
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2

    def get_window_handle():
        return pygame.display.get_wm_info()["window"]

    def set_window_position(x, y, width, height):
        hwnd = get_window_handle()
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            ctypes.wintypes.HWND(HWND_NOTOPMOST),
            x,
            y,
            width,
            height,
            SWP_SHOWWINDOW | SWP_FRAMECHANGED
        )

# --- Audio Callback Function ---
def audio_callback(indata, frames, time, status):
    if status:
        pass
    global audio_data_buffer
    audio_data_buffer = indata.flatten()

# --- Color Gradient Function ---
def get_gradient_color(colors, percentage):
    if not colors:
        return (0,0,0)
    
    num_colors = len(colors)
    if num_colors == 1:
        return colors[0]

    step = 1.0 / (num_colors - 1)
    
    if percentage <= 0: return colors[0]
    if percentage >= 1: return colors[-1]

    for i in range(num_colors - 1):
        if percentage >= i * step and percentage <= (i + 1) * step:
            local_percent = (percentage - i * step) / step
            color1 = colors[i]
            color2 = colors[i+1]
            r = int(color1[0] + (color2[0] - color1[0]) * local_percent)
            g = int(color1[1] + (color2[1] - color1[1]) * local_percent)
            b = int(color1[2] + (color2[2] - color1[2]) * local_percent)
            return (r, g, b)
    return colors[-1]

# --- Oscilloscope Drawing Function ---
def draw_oscilloscope(screen, audio_data_buffer, colors, gradient_active):
    current_width, current_height = screen.get_size()
    center_y = current_height / 2
    
    if audio_data_buffer is None or len(audio_data_buffer) == 0:
        if colors:
            pygame.draw.line(screen, colors[0], (0, int(center_y)), (current_width, int(center_y)), 2)
        return

    cleaned_audio_buffer = np.nan_to_num(audio_data_buffer, copy=True, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    max_abs_val = np.max(np.abs(cleaned_audio_buffer))
    
    if max_abs_val == 0:
        if colors:
            pygame.draw.line(screen, colors[0], (0, int(center_y)), (current_width, int(center_y)), 2)
        return
        
    scaling_factor = (current_height / 2.0) / max_abs_val * 0.9

    points = []
    for i in range(len(cleaned_audio_buffer)):
        x = i * current_width / len(cleaned_audio_buffer)
        y = center_y - cleaned_audio_buffer[i] * scaling_factor
        points.append((int(x), int(y)))
    
    if len(points) > 1:
        if gradient_active and len(colors) > 1:
            for i in range(len(points) - 1):
                start_point = points[i]
                end_point = points[i+1]
                percentage = i / (len(points) - 2) if len(points) > 2 else 0
                color = get_gradient_color(colors, percentage)
                pygame.draw.line(screen, color, start_point, end_point, 2)
        else:
            color = colors[0] if colors else (0,0,0)
            pygame.draw.lines(screen, color, False, points, 2)

# --- Spectrogram Drawing Function ---
def draw_spectrogram(screen, spectrogram_buffer, colors, gradient_active):
    current_width, current_height = screen.get_size()
    
    if not spectrogram_buffer:
        return
    
    # Get the max magnitude to scale colors
    max_mag = 0
    for column in spectrogram_buffer:
        if column.size > 0:
            max_mag = max(max_mag, np.max(column))
    
    if max_mag == 0:
        return

    bar_width = max(1, int(current_width / SPECTROGRAM_BUFFER_SIZE))
    x_start = current_width - len(spectrogram_buffer) * bar_width
    
    for i, column in enumerate(spectrogram_buffer):
        x = x_start + i * bar_width
        
        # Scale magnitudes to a 0-1 range for color mapping
        scaled_column = np.log10(column + 1e-9) # Add a small value to avoid log(0)
        scaled_column = (scaled_column - np.min(scaled_column)) / (np.max(scaled_column) - np.min(scaled_column))

        # Draw each frequency bin as a pixel
        for j, magnitude in enumerate(scaled_column):
            y = current_height - int(j * (current_height / len(scaled_column))) - 1
            if y < 0: continue
            
            if gradient_active:
                color_percentage = magnitude * GAIN_FACTOR * 0.2
                color = get_gradient_color(colors, color_percentage)
            else:
                # Map magnitude to brightness of the base color
                base_color = colors[0] if colors else (255, 255, 255)
                brightness = min(255, int(magnitude * 255 * GAIN_FACTOR * 0.2))
                color = (int(base_color[0] * brightness/255), int(base_color[1] * brightness/255), int(base_color[2] * brightness/255))
            
            pygame.draw.rect(screen, color, (x, y, bar_width, int(current_height/len(scaled_column))))

# --- Settings Screen UI Elements and State ---
settings_ui = {}
settings_font = pygame.font.Font(None, 24)
slider_dragging = None

def init_settings_ui():
    global settings_ui
    screen_width, screen_height = screen.get_size()
    settings_ui.clear()
    padding = 20
    y_pos = padding

    def create_slider(label, y, var_name, min_val, max_val, color_index=None, color_comp=None):
        slider_rect = pygame.Rect(screen_width // 2 + 100, y, 200, 20)
        value_rect = pygame.Rect(slider_rect.right + 10, y, 50, 20)
        label_rect = pygame.Rect(padding, y, screen_width // 2 - padding - 10, 20)
        settings_ui[f'slider_{var_name}_{color_index}_{color_comp}'] = {
            'type': 'slider',
            'rect': slider_rect,
            'label_text': label,
            'value_rect': value_rect,
            'var_name': var_name,
            'min': min_val,
            'max': max_val,
            'color_index': color_index,
            'color_comp': color_comp
        }
        return y + 30

    def create_button(label, y, action, width=200):
        button_rect = pygame.Rect(screen_width // 2 - width // 2, y, width, 40)
        settings_ui[f'button_{action}'] = {
            'type': 'button',
            'rect': button_rect,
            'label_text': label,
            'action': action
        }
        return y + 50
        
    def create_toggle(label, y, var_name):
        checkbox_rect = pygame.Rect(screen_width // 2 + 100, y, 20, 20)
        label_rect = pygame.Rect(padding, y, screen_width // 2 - padding - 10, 20)
        settings_ui[f'toggle_{var_name}'] = {
            'type': 'toggle',
            'rect': checkbox_rect,
            'label_text': label,
            'var_name': var_name
        }
        return y + 30

    def create_color_count_buttons(label, y, var_name):
        label_rect = pygame.Rect(padding, y, screen_width // 2 - padding - 10, 20)
        settings_ui[f'label_{var_name}_count'] = {'type': 'label', 'rect': label_rect, 'text': label}
        
        button_y = y - 5
        buttons_x_start = screen_width // 2 + 100
        for i in range(1, 4):
            button_rect = pygame.Rect(buttons_x_start + (i-1)*50, button_y, 40, 30)
            settings_ui[f'button_{var_name}_count_{i}'] = {
                'type': 'button_color_count',
                'rect': button_rect,
                'label_text': str(i),
                'action': f'set_{var_name}_count',
                'value': i
            }
        return y + 30
    
    def create_color_preview(y, var_name):
        preview_rect = pygame.Rect(screen_width // 2 - 50, y, 100, 50)
        settings_ui[f'preview_{var_name}'] = {
            'type': 'color_preview',
            'rect': preview_rect,
            'var_name': var_name
        }
        return y + 60

    y_pos = create_toggle("Spectrogram Active", y_pos, "SPECTROGRAM_ACTIVE")
    y_pos = create_color_count_buttons("Spectrogram Colors", y_pos, "spectrogram")
    for i in range(SPECTROGRAM_COLOR_COUNT):
        y_pos = create_color_preview(y_pos, f"SPECTROGRAM_COLORS[{i}]")
        y_pos = create_slider(f"Spectrogram Color {i+1} R", y_pos, 'spectrogram_color', 0, 255, i, 0)
        y_pos = create_slider(f"Spectrogram Color {i+1} G", y_pos, 'spectrogram_color', 0, 255, i, 1)
        y_pos = create_slider(f"Spectrogram Color {i+1} B", y_pos, 'spectrogram_color', 0, 255, i, 2)
    y_pos = create_toggle("Spectrogram Gradient", y_pos, "SPECTROGRAM_GRADIENT_ACTIVE")
    
    y_pos = create_toggle("Oscilloscope Active", y_pos, "OSCILLOSCOPE_ACTIVE")
    y_pos = create_color_count_buttons("Oscilloscope Colors", y_pos, "oscilloscope")
    # Oscilloscope Color Sliders
    for i in range(OSCILLOSCOPE_COLOR_COUNT):
        y_pos = create_color_preview(y_pos, f"OSCILLOSCOPE_COLORS[{i}]")
        y_pos = create_slider(f"Oscilloscope Color {i+1} R", y_pos, 'oscilloscope_color', 0, 255, i, 0)
        y_pos = create_slider(f"Oscilloscope Color {i+1} G", y_pos, 'oscilloscope_color', 0, 255, i, 1)
        y_pos = create_slider(f"Oscilloscope Color {i+1} B", y_pos, 'oscilloscope_color', 0, 255, i, 2)
    y_pos = create_toggle("Oscilloscope Gradient", y_pos, "OSCILLOSCOPE_GRADIENT_ACTIVE")

    y_pos = create_toggle("Spectrum Active", y_pos, "SPECTRUM_ACTIVE")
    y_pos = create_color_count_buttons("Spectrum Colors", y_pos, "spectrum")
    
    # Spectrum Color Sliders
    for i in range(SPECTRUM_COLOR_COUNT):
        y_pos = create_color_preview(y_pos, f"SPECTRUM_COLORS[{i}]")
        y_pos = create_slider(f"Spectrum Color {i+1} R", y_pos, 'spectrum_color', 0, 255, i, 0)
        y_pos = create_slider(f"Spectrum Color {i+1} G", y_pos, 'spectrum_color', 0, 255, i, 1)
        y_pos = create_slider(f"Spectrum Color {i+1} B", y_pos, 'spectrum_color', 0, 255, i, 2)
    y_pos = create_toggle("Spectrum Gradient", y_pos, "SPECTRUM_GRADIENT_ACTIVE")
    
    y_pos = create_slider("Gain Factor", y_pos, "GAIN_FACTOR", 1, 20)
    y_pos = create_button("Back to Main", y_pos, "main")
    y_pos = create_button("Save Settings", y_pos, "save_settings")
    y_pos = create_button("Load Settings", y_pos, "load_settings")
    y_pos = create_button("Toggle Fullscreen (F11)", y_pos, "toggle_fullscreen")
    y_pos = create_button("Exit", y_pos, "exit")

def draw_settings_screen():
    global settings_ui
    screen.fill(BACKGROUND_COLOR)
    
    for key, ui_element in settings_ui.items():
        element_type = ui_element['type']
        
        if element_type == 'label':
            text_surface = settings_font.render(ui_element['text'], True, (255, 255, 255))
            screen.blit(text_surface, ui_element['rect'])
        
        elif element_type == 'slider':
            label_surface = settings_font.render(ui_element['label_text'], True, (255, 255, 255))
            screen.blit(label_surface, ui_element['rect'].move(-300, 0))

            pygame.draw.rect(screen, (100, 100, 100), ui_element['rect'])
            
            val = globals().get(ui_element['var_name'], None)
            if val is None:
                if 'color_index' in ui_element and 'color_comp' in ui_element:
                    if ui_element['var_name'] == 'spectrum_color':
                        val = SPECTRUM_COLORS[ui_element['color_index']][ui_element['color_comp']]
                    elif ui_element['var_name'] == 'oscilloscope_color':
                        val = OSCILLOSCOPE_COLORS[ui_element['color_index']][ui_element['color_comp']]
                    else: # spectrogram_color
                        val = SPECTROGRAM_COLORS[ui_element['color_index']][ui_element['color_comp']]
            
            if val is not None:
                percent = (val - ui_element['min']) / (ui_element['max'] - ui_element['min'])
                handle_x = ui_element['rect'].x + percent * ui_element['rect'].width
                pygame.draw.circle(screen, (255, 255, 255), (int(handle_x), ui_element['rect'].centery), 10)
                
                value_surface = settings_font.render(str(int(val)), True, (255, 255, 255))
                screen.blit(value_surface, ui_element['value_rect'])

        elif element_type == 'button':
            pygame.draw.rect(screen, (100, 100, 100), ui_element['rect'])
            label_surface = settings_font.render(ui_element['label_text'], True, (255, 255, 255))
            text_rect = label_surface.get_rect(center=ui_element['rect'].center)
            screen.blit(label_surface, text_rect)
            
        elif element_type == 'toggle':
            label_surface = settings_font.render(ui_element['label_text'], True, (255, 255, 255))
            screen.blit(label_surface, ui_element['rect'].move(-300, 0))
            pygame.draw.rect(screen, (100, 100, 100), ui_element['rect'], 2)
            if globals()[ui_element['var_name']]:
                pygame.draw.rect(screen, (0, 255, 0), ui_element['rect'].inflate(-4, -4))
                
        elif element_type == 'button_color_count':
            label_surface = settings_font.render(ui_element['label_text'], True, (255, 255, 255))
            text_rect = label_surface.get_rect(center=ui_element['rect'].center)
            is_active = (
                (ui_element['value'] == SPECTRUM_COLOR_COUNT and 'spectrum' in ui_element['action']) or
                (ui_element['value'] == OSCILLOSCOPE_COLOR_COUNT and 'oscilloscope' in ui_element['action']) or
                (ui_element['value'] == SPECTROGRAM_COLOR_COUNT and 'spectrogram' in ui_element['action'])
            )
            color = (0, 150, 0) if is_active else (100, 100, 100)
            pygame.draw.rect(screen, color, ui_element['rect'])
            screen.blit(label_surface, text_rect)

        elif element_type == 'color_preview':
            try:
                color_var_name = ui_element['var_name']
                color_val = eval(color_var_name)
                pygame.draw.rect(screen, color_val, ui_element['rect'])
                pygame.draw.rect(screen, (255, 255, 255), ui_element['rect'], 2)
            except NameError:
                pass


def handle_settings_click(pos):
    global app_state, slider_dragging, GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, \
           OSCILLOSCOPE_COLOR_COUNT, SPECTRUM_COLOR_COUNT, SPECTROGRAM_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, SPECTRUM_GRADIENT_ACTIVE, SPECTROGRAM_GRADIENT_ACTIVE
    
    for key, ui_element in settings_ui.items():
        if ui_element['type'] == 'slider' and ui_element['rect'].collidepoint(pos):
            slider_dragging = ui_element
            return
        
        if ui_element['type'] == 'button' and ui_element['rect'].collidepoint(pos):
            action = ui_element['action']
            if action == 'main':
                app_state = APP_STATE_MAIN
            elif action == 'save_settings':
                save_settings()
            elif action == 'load_settings':
                load_settings()
                init_settings_ui()
            elif action == 'toggle_fullscreen':
                toggle_fullscreen()
            elif action == 'exit':
                pygame.quit()
                sys.exit()

        if ui_element['type'] == 'toggle' and ui_element['rect'].collidepoint(pos):
            var_name = ui_element['var_name']
            if var_name == "OSCILLOSCOPE_GRADIENT_ACTIVE":
                OSCILLOSCOPE_GRADIENT_ACTIVE = not OSCILLOSCOPE_GRADIENT_ACTIVE
            elif var_name == "SPECTRUM_GRADIENT_ACTIVE":
                SPECTRUM_GRADIENT_ACTIVE = not SPECTRUM_GRADIENT_ACTIVE
            elif var_name == "SPECTROGRAM_GRADIENT_ACTIVE":
                SPECTROGRAM_GRADIENT_ACTIVE = not SPECTROGRAM_GRADIENT_ACTIVE
            elif var_name == "OSCILLOSCOPE_ACTIVE":
                OSCILLOSCOPE_ACTIVE = not OSCILLOSCOPE_ACTIVE
            elif var_name == "SPECTRUM_ACTIVE":
                SPECTRUM_ACTIVE = not SPECTRUM_ACTIVE
            elif var_name == "SPECTROGRAM_ACTIVE":
                SPECTROGRAM_ACTIVE = not SPECTROGRAM_ACTIVE

        if ui_element['type'] == 'button_color_count' and ui_element['rect'].collidepoint(pos):
            action = ui_element['action']
            value = ui_element['value']
            if 'spectrum' in action:
                SPECTRUM_COLOR_COUNT = value
                if len(SPECTRUM_COLORS) < value:
                    for _ in range(value - len(SPECTRUM_COLORS)):
                        SPECTRUM_COLORS.append((255, 255, 255))
                elif len(SPECTRUM_COLORS) > value:
                    SPECTRUM_COLORS[:] = SPECTRUM_COLORS[:value]
            elif 'oscilloscope' in action:
                OSCILLOSCOPE_COLOR_COUNT = value
                if len(OSCILLOSCOPE_COLORS) < value:
                    for _ in range(value - len(OSCILLOSCOPE_COLORS)):
                        OSCILLOSCOPE_COLORS.append((255, 255, 255))
                elif len(OSCILLOSCOPE_COLORS) > value:
                    OSCILLOSCOPE_COLORS[:] = OSCILLOSCOPE_COLORS[:value]
            elif 'spectrogram' in action:
                SPECTROGRAM_COLOR_COUNT = value
                if len(SPECTROGRAM_COLORS) < value:
                    for _ in range(value - len(SPECTROGRAM_COLORS)):
                        SPECTROGRAM_COLORS.append((255, 255, 255))
                elif len(SPECTROGRAM_COLORS) > value:
                    SPECTROGRAM_COLORS[:] = SPECTROGRAM_COLORS[:value]
            init_settings_ui()

def handle_slider_drag(pos):
    global slider_dragging
    if slider_dragging:
        x_norm = (pos[0] - slider_dragging['rect'].x) / slider_dragging['rect'].width
        x_norm = max(0.0, min(1.0, x_norm))
        value = int(slider_dragging['min'] + x_norm * (slider_dragging['max'] - slider_dragging['min']))
        
        var_name = slider_dragging['var_name']
        if var_name == "GAIN_FACTOR":
            globals()[var_name] = float(value)
        elif 'color' in var_name:
            color_list = None
            if 'spectrum' in var_name:
                color_list = SPECTRUM_COLORS
            elif 'oscilloscope' in var_name:
                color_list = OSCILLOSCOPE_COLORS
            elif 'spectrogram' in var_name:
                color_list = SPECTROGRAM_COLORS

            if color_list:
                color_index = slider_dragging['color_index']
                color_comp = slider_dragging['color_comp']
                
                current_color = list(color_list[color_index])
                current_color[color_comp] = value
                color_list[color_index] = tuple(current_color)

# --- Pop-up Menu Variables ---
MENU_ACTIVE = False
MENU_X = 0
MENU_Y = 0
MENU_FONT = pygame.font.Font(None, 24)

def get_menu_options():
    return [
        {"text": f"Toggle Spectrogram ({'ON' if SPECTROGRAM_ACTIVE else 'OFF'})", "action": "toggle_spectrogram"},
        {"text": f"Toggle Oscilloscope ({'ON' if OSCILLOSCOPE_ACTIVE else 'OFF'})", "action": "toggle_oscilloscope"},
        {"text": f"Toggle Spectrum Analyzer ({'ON' if SPECTRUM_ACTIVE else 'OFF'})", "action": "toggle_spectrum"},
        {"text": "---", "action": "separator"},
        {"text": "Open Settings", "action": "open_settings"},
        {"text": "Exit", "action": "exit"}
    ]

MENU_ITEM_HEIGHT = 30
MENU_PADDING = 10
MENU_BACKGROUND_COLOR = (50, 50, 50)
MENU_TEXT_COLOR = (255, 255, 255)

# --- Menu Drawing Function ---
def draw_menu():
    global screen_size, MENU_OPTIONS_RECTS
    if not MENU_ACTIVE:
        return
    
    MENU_OPTIONS = get_menu_options()
    MENU_OPTIONS_RECTS = []

    max_text_width = max([MENU_FONT.size(option["text"])[0] for option in MENU_OPTIONS])
    menu_width = max_text_width + (2 * MENU_PADDING)
    menu_height = len(MENU_OPTIONS) * MENU_ITEM_HEIGHT + (2 * MENU_PADDING)

    draw_x = MENU_X
    draw_y = MENU_Y
    if draw_x + menu_width > screen_size[0]:
        draw_x = screen_size[0] - menu_width
    if draw_y + menu_height > screen_size[1]:
        draw_y = screen_size[1] - menu_height

    menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
    menu_surface.fill((50, 50, 50, 230))
    pygame.draw.rect(menu_surface, (200, 200, 200, 255), menu_surface.get_rect(), 1)

    for i, option in enumerate(MENU_OPTIONS):
        if option["action"] == "separator":
            pygame.draw.line(menu_surface, (100, 100, 100), (MENU_PADDING, MENU_PADDING + i * MENU_ITEM_HEIGHT), (menu_width - MENU_PADDING, MENU_PADDING + i * MENU_ITEM_HEIGHT), 1)
            continue
        
        text_surface = MENU_FONT.render(option["text"], True, MENU_TEXT_COLOR)
        text_rect = text_surface.get_rect(midleft=(MENU_PADDING, MENU_PADDING + i * MENU_ITEM_HEIGHT + MENU_ITEM_HEIGHT / 2))
        menu_surface.blit(text_surface, text_rect)
        option_rect = pygame.Rect(draw_x, draw_y + (MENU_PADDING + i * MENU_ITEM_HEIGHT), menu_width, MENU_ITEM_HEIGHT)
        MENU_OPTIONS_RECTS.append({'rect': option_rect, 'action': option['action']})

    screen.blit(menu_surface, (draw_x, draw_y))
    globals()['menu_rect'] = pygame.Rect(draw_x, draw_y, menu_width, menu_height)

# --- Menu Click Handler ---
def handle_menu_click(mouse_pos):
    global MENU_ACTIVE, app_state, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE
    
    if not MENU_ACTIVE:
        return
    
    # Check if the click is outside the menu to close it
    menu_rect = globals().get('menu_rect')
    if menu_rect is None or not menu_rect.collidepoint(mouse_pos):
        MENU_ACTIVE = False
        return

    # Check if the click is on a menu item
    for option_data in globals().get('MENU_OPTIONS_RECTS', []):
        if option_data['rect'].collidepoint(mouse_pos):
            MENU_ACTIVE = False
            action = option_data['action']
            if action == "toggle_spectrogram":
                SPECTROGRAM_ACTIVE = not SPECTROGRAM_ACTIVE
            elif action == "toggle_oscilloscope":
                OSCILLOSCOPE_ACTIVE = not OSCILLOSCOPE_ACTIVE
            elif action == "toggle_spectrum":
                SPECTRUM_ACTIVE = not SPECTRUM_ACTIVE
            elif action == "open_settings":
                app_state = APP_STATE_SETTINGS
                init_settings_ui()
            elif action == "exit":
                pygame.quit()
                sys.exit()
            return

# --- Fullscreen Toggle Function ---
def toggle_fullscreen():
    global is_fullscreen, screen, screen_size, last_window_width, last_window_height, last_window_x, last_window_y

    is_fullscreen = not is_fullscreen

    if is_fullscreen:
        last_window_width, last_window_height = screen.get_size()
        try:
            last_window_x, last_window_y = pygame.display.get_window_position()
        except Exception:
            pass
        
        desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
        screen = pygame.display.set_mode((desktop_width, desktop_height), pygame.NOFRAME)
        screen_size = (desktop_width, desktop_height)
        
        if sys.platform == "win32":
            try:
                set_window_position(0, 0, desktop_width, desktop_height)
            except Exception as e:
                print(f"Error using ctypes to set window position: {e}", file=sys.stderr)
        
    else:
        screen = pygame.display.set_mode((last_window_width, last_window_height), pygame.RESIZABLE)
        screen_size = (last_window_width, last_window_height)
        
        if sys.platform == "win32":
            try:
                set_window_position(last_window_x, last_window_y, last_window_width, last_window_height)
            except Exception as e:
                print(f"Error using ctypes to restore window position: {e}", file=sys.stderr)

# --- Main Loop ---
def main():
    global audio_data_buffer, MENU_ACTIVE, MENU_X, MENU_Y, running, screen, screen_size, app_state, slider_dragging
    
    try:
        with sd.InputStream(samplerate=SAMPLING_RATE, channels=2, callback=audio_callback, blocksize=CHUNK_SIZE, device=DEVICE_ID):
            print(f"Listening to device index {DEVICE_ID} ('What U Hear')... Sample Rate: {SAMPLING_RATE} Hz")
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 3:  # Right-click
                            if app_state == APP_STATE_MAIN:
                                MENU_ACTIVE = not MENU_ACTIVE
                                MENU_X, MENU_Y = event.pos
                        elif event.button == 1:  # Left-click
                            if app_state == APP_STATE_SETTINGS:
                                handle_settings_click(event.pos)
                            elif MENU_ACTIVE:
                                handle_menu_click(event.pos)
                            else: # If menu is not active and we click, close the menu
                                MENU_ACTIVE = False
                    elif event.type == pygame.MOUSEBUTTONUP:
                        slider_dragging = None
                    elif event.type == pygame.MOUSEMOTION:
                        if app_state == APP_STATE_SETTINGS and slider_dragging:
                            handle_slider_drag(event.pos)
                    elif event.type == pygame.VIDEORESIZE:
                        if not is_fullscreen and app_state == APP_STATE_MAIN:
                            screen_size = event.size
                            screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_F11:
                            toggle_fullscreen()
                
                if app_state == APP_STATE_MAIN:
                    screen.fill(BACKGROUND_COLOR)
                    
                    if 'audio_data_buffer' in globals() and audio_data_buffer is not None:
                        # Process audio data for visualizations
                        cleaned_audio_buffer = np.nan_to_num(audio_data_buffer, copy=True, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

                        # Spectrogram
                        if SPECTROGRAM_ACTIVE:
                            f, t_spec, Sxx = spectrogram(cleaned_audio_buffer, SAMPLING_RATE, nperseg=256, noverlap=128)
                            spectrogram_buffer.append(Sxx[:, 0]) # Append the first column (newest time slice)
                            draw_spectrogram(screen, spectrogram_buffer, SPECTROGRAM_COLORS, SPECTROGRAM_GRADIENT_ACTIVE)

                        # Oscilloscope
                        if OSCILLOSCOPE_ACTIVE:
                            draw_oscilloscope(screen, cleaned_audio_buffer, OSCILLOSCOPE_COLORS, OSCILLOSCOPE_GRADIENT_ACTIVE)

                        # Spectrum
                        if SPECTRUM_ACTIVE:
                            N = len(cleaned_audio_buffer)
                            yf = fft(cleaned_audio_buffer * np.hanning(N))
                            magnitudes = 2.0/N * np.abs(yf[0:N//2])

                            BAR_WIDTH = max(1, int(screen_size[0] / (TARGET_BAR_COUNT * 1.5)))
                            BAR_SPACING = max(1, int(BAR_WIDTH * 0.2))
                            
                            num_bars = int(screen_size[0] / (BAR_WIDTH + BAR_SPACING))
                            if num_bars <= 0:
                                num_bars = 1

                            for i in range(num_bars):
                                freq_bin_start = int(i * (N / 2) / num_bars)
                                freq_bin_end = int((i + 1) * (N / 2) / num_bars)
                                
                                if freq_bin_start < len(magnitudes) and freq_bin_start < freq_bin_end:
                                    bar_magnitude = np.max(magnitudes[freq_bin_start:freq_bin_end])
                                else:
                                    bar_magnitude = 0.0

                                bar_height = int(np.power(bar_magnitude, 0.5) * screen_size[1] * GAIN_FACTOR)
                                bar_height = max(0, min(bar_height, screen_size[1]))

                                x = i * (BAR_WIDTH + BAR_SPACING)
                                y = screen_size[1] - bar_height

                                if SPECTRUM_GRADIENT_ACTIVE:
                                    for h_pixel in range(min(bar_height, screen_size[1])):
                                        percentage = h_pixel / bar_height if bar_height else 0
                                        color = get_gradient_color(SPECTRUM_COLORS, percentage)
                                        y_pos = screen_size[1] - 1 - h_pixel
                                        if y_pos >= 0:
                                            pygame.draw.rect(screen, color, (x, y_pos, BAR_WIDTH, 1))
                                else:
                                    color = SPECTRUM_COLORS[0] if SPECTRUM_COLORS else (0,0,0)
                                    pygame.draw.rect(screen, color, (x, y, BAR_WIDTH, bar_height))

                    draw_menu()
                
                elif app_state == APP_STATE_SETTINGS:
                    draw_settings_screen()

                pygame.display.flip()
                clock.tick(60)

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        save_settings()
        pygame.quit()

if __name__ == "__main__":
    audio_data_buffer = None
    main()
