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

SETTINGS_FILE = 'settings.ini'
config = configparser.ConfigParser()
config.read(SETTINGS_FILE)

# Get the settings with fallbacks to default values
nperseg_setting = config.getint('Spectrogram', 'nperseg', fallback=256)
noverlap_setting = config.getint('Spectrogram', 'noverlap', fallback=128)

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
SPECTROGRAM_BUFFER_SIZE = 200 # Number of spectrogram columns to store, speed

# --- Global Variables for Color Theme
SPECTRUM_THEMES = ["Fire", "Ice", "Melon", "Halloween", "Dracula","Frog","Custom"]
SELECTED_SPECTRUM_THEME = "Custom" # Default selected theme

# --- Global Variables for Window State ---
INITIAL_SCREEN_WIDTH = 1250
INITIAL_SCREEN_HEIGHT = 750
last_window_width = INITIAL_SCREEN_WIDTH
last_window_height = INITIAL_SCREEN_HEIGHT
last_window_x = 100
last_window_y = 100
is_fullscreen = False
screen_size = (INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT)

# --- Spectrogram Buffer ---
spectrogram_buffer = collections.deque(maxlen=SPECTROGRAM_BUFFER_SIZE)

# --- Reset Default Settings ---
def reset_default_settings():
    global GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, BACKGROUND_COLOR, \
           OSCILLOSCOPE_COLORS, OSCILLOSCOPE_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, \
           SPECTRUM_COLORS, SPECTRUM_COLOR_COUNT, SPECTRUM_GRADIENT_ACTIVE, \
           SPECTROGRAM_COLORS, SPECTROGRAM_COLOR_COUNT, SPECTROGRAM_GRADIENT_ACTIVE, \
           SELECTED_SPECTRUM_THEME
    
    GAIN_FACTOR = 5.0
    OSCILLOSCOPE_ACTIVE = True
    SPECTRUM_ACTIVE = True
    SPECTROGRAM_ACTIVE = True
    BACKGROUND_COLOR = (0, 0, 0)
    
    OSCILLOSCOPE_COLORS = [(0, 0, 255)]
    OSCILLOSCOPE_COLOR_COUNT = 1
    OSCILLOSCOPE_GRADIENT_ACTIVE = False
    
    SPECTROGRAM_COLORS = [(255, 0, 0)]
    SPECTROGRAM_COLOR_COUNT = 1
    SPECTROGRAM_GRADIENT_ACTIVE = False
    
    SELECTED_SPECTRUM_THEME = "Custom"
    apply_spectrum_theme(SELECTED_SPECTRUM_THEME)


# --- Save a specific theme to the config object ---
def save_spectrum_theme(theme_name, colors, color_count, gradient_active):
    if theme_name not in config:
        config[theme_name] = {}
    config[theme_name]['spectrum_color_count'] = str(color_count)
    config[theme_name]['spectrum_gradient_active'] = str(gradient_active)
    for i, color in enumerate(colors):
        config[theme_name][f'spectrum_color_{i+1}'] = str(color)

# --- Save Settings ---
def save_settings():
    # Only save the main application settings and the "Custom" theme.
    
    # 1. Update the [SpectrumAnalyzer] section with current settings
    if 'SpectrumAnalyzer' not in config:
        config['SpectrumAnalyzer'] = {}
    
    config['SpectrumAnalyzer']['selected_spectrum_theme'] = SELECTED_SPECTRUM_THEME
    config['SpectrumAnalyzer']['gain_factor'] = str(GAIN_FACTOR)
    config['SpectrumAnalyzer']['oscilloscope_active'] = str(OSCILLOSCOPE_ACTIVE)
    config['SpectrumAnalyzer']['spectrum_active'] = str(SPECTRUM_ACTIVE)
    config['SpectrumAnalyzer']['spectrogram_active'] = str(SPECTROGRAM_ACTIVE)
    config['SpectrumAnalyzer']['background_color'] = str(BACKGROUND_COLOR)
    
    # ... (Keep the rest of the existing code for Oscilloscope and Spectrogram colors)
    config['SpectrumAnalyzer']['oscilloscope_color_count'] = str(OSCILLOSCOPE_COLOR_COUNT)
    config['SpectrumAnalyzer']['oscilloscope_gradient_active'] = str(OSCILLOSCOPE_GRADIENT_ACTIVE)
    for i, color in enumerate(OSCILLOSCOPE_COLORS):
        config['SpectrumAnalyzer'][f'oscilloscope_color_{i+1}'] = str(color)
        
    config['SpectrumAnalyzer']['spectrogram_color_count'] = str(SPECTROGRAM_COLOR_COUNT)
    config['SpectrumAnalyzer']['spectrogram_gradient_active'] = str(SPECTROGRAM_GRADIENT_ACTIVE)
    for i, color in enumerate(SPECTROGRAM_COLORS):
        config['SpectrumAnalyzer'][f'spectrogram_color_{i+1}'] = str(color)

    # 2. Only save the 'Custom' theme if it is the currently selected theme.
    # The presets will not be overwritten.
    if SELECTED_SPECTRUM_THEME == "Custom":
        if 'Custom' not in config:
            config['Custom'] = {}
        config['Custom']['spectrum_color_count'] = str(SPECTRUM_COLOR_COUNT)
        config['Custom']['spectrum_gradient_active'] = str(SPECTRUM_GRADIENT_ACTIVE)
        for i, color in enumerate(SPECTRUM_COLORS):
            config['Custom'][f'spectrum_color_{i+1}'] = str(color)

    # 3. Write the updated config back to the file.
    try:
        # Use 'with open' to ensure the file is closed properly
        with open(SETTINGS_FILE, 'w') as configfile:
            config.write(configfile)
        print(f"Settings saved to {SETTINGS_FILE}.")
    except Exception as e:
        print(f"Error saving {SETTINGS_FILE}: {e}", file=sys.stderr)

# --- Load Settings ---
def load_settings():
    # ... (rest of your load_settings function, as provided in the previous step) ...
    global GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, BACKGROUND_COLOR, \
           OSCILLOSCOPE_COLORS, OSCILLOSCOPE_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, \
           SPECTROGRAM_COLORS, SPECTROGRAM_COLOR_COUNT, SPECTROGRAM_GRADIENT_ACTIVE, \
           SELECTED_SPECTRUM_THEME

    if 'SpectrumAnalyzer' in config:
        try:
            GAIN_FACTOR = float(config['SpectrumAnalyzer'].get('gain_factor', GAIN_FACTOR))
            OSCILLOSCOPE_ACTIVE = config['SpectrumAnalyzer'].getboolean('oscilloscope_active', OSCILLOSCOPE_ACTIVE)
            SPECTRUM_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrum_active', SPECTRUM_ACTIVE)
            SPECTROGRAM_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrogram_active', SPECTROGRAM_ACTIVE)
            BACKGROUND_COLOR = eval(config['SpectrumAnalyzer'].get('background_color', str(BACKGROUND_COLOR)))
            
            SELECTED_SPECTRUM_THEME = config['SpectrumAnalyzer'].get('selected_spectrum_theme', SELECTED_SPECTRUM_THEME)
            apply_spectrum_theme(SELECTED_SPECTRUM_THEME)

            OSCILLOSCOPE_COLOR_COUNT = int(config['SpectrumAnalyzer'].get('oscilloscope_color_count', OSCILLOSCOPE_COLOR_COUNT))
            OSCILLOSCOPE_GRADIENT_ACTIVE = config['SpectrumAnalyzer'].getboolean('oscilloscope_gradient_active', OSCILLOSCOPE_GRADIENT_ACTIVE)
            OSCILLOSCOPE_COLORS = [eval(config['SpectrumAnalyzer'][f'oscilloscope_color_{i+1}']) for i in range(OSCILLOSCOPE_COLOR_COUNT)]
            
            SPECTROGRAM_COLOR_COUNT = int(config['SpectrumAnalyzer'].get('spectrogram_color_count', SPECTROGRAM_COLOR_COUNT))
            SPECTROGRAM_GRADIENT_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrogram_gradient_active', SPECTROGRAM_GRADIENT_ACTIVE)
            SPECTROGRAM_COLORS = [eval(config['SpectrumAnalyzer'][f'spectrogram_color_{i+1}']) for i in range(SPECTROGRAM_COLOR_COUNT)]
            
            print(f"Settings loaded from {SETTINGS_FILE}.")

        except Exception as e:
            print(f"Error reading {SETTINGS_FILE}: {e}. Using default settings.", file=sys.stderr)
            reset_default_settings()
            save_settings()
    else:
        print(f"Info: [SpectrumAnalyzer] section not found in {SETTINGS_FILE}. Using defaults.")
        reset_default_settings()
        save_settings()

# --- Reset Default Settings ---
def reset_default_settings():
    global GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, BACKGROUND_COLOR, \
           OSCILLOSCOPE_COLORS, OSCILLOSCOPE_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, \
           SPECTRUM_COLORS, SPECTRUM_COLOR_COUNT, SPECTRUM_GRADIENT_ACTIVE, \
           SPECTROGRAM_COLORS, SPECTROGRAM_COLOR_COUNT, SPECTROGRAM_GRADIENT_ACTIVE, \
           SELECTED_SPECTRUM_THEME
    
    GAIN_FACTOR = 5.0
    OSCILLOSCOPE_ACTIVE = True
    SPECTRUM_ACTIVE = True
    SPECTROGRAM_ACTIVE = True
    BACKGROUND_COLOR = (0, 0, 0)
    
    OSCILLOSCOPE_COLORS = [(0, 0, 255)]
    OSCILLOSCOPE_COLOR_COUNT = 1
    OSCILLOSCOPE_GRADIENT_ACTIVE = False
    
    SPECTROGRAM_COLORS = [(255, 0, 0)]
    SPECTROGRAM_COLOR_COUNT = 1
    SPECTROGRAM_GRADIENT_ACTIVE = False
    
    # Reset the selected theme and apply its colors
    SELECTED_SPECTRUM_THEME = "Custom"
    apply_spectrum_theme(SELECTED_SPECTRUM_THEME)



# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Spectrum Analyzer")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 28)

WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

#my own fix for aligning the spectrogram at launch
screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)

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

        # Check for a zero denominator to prevent division by zero
        denominator = np.max(scaled_column) - np.min(scaled_column)

        if denominator == 0:
            scaled_column = np.zeros_like(scaled_column)
        else:
            scaled_column = (scaled_column - np.min(scaled_column)) / denominator

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
                brightness = min(255, int(magnitude * 255 * GAIN_FACTOR * 1.0))   # *0.2 default, i changed to 1.0
                color = (int(base_color[0] * brightness/255), int(base_color[1] * brightness/255), int(base_color[2] * brightness/255))
            
            pygame.draw.rect(screen, color, (x, y, bar_width, int(current_height/len(scaled_column))))

# --- Settings Screen UI Elements and State ---
settings_ui = {}
slider_dragging = None

def draw_label(text, pos, bold=False):
    surf = (big_font if bold else font).render(text, True, WHITE)
    screen.blit(surf, pos)

def draw_button(text, rect, color=DARK_GRAY):
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, WHITE, rect, 2)
    label = font.render(text, True, WHITE)
    label_rect = label.get_rect(center=rect.center)
    screen.blit(label, label_rect)

def draw_checkbox(checked, pos):
    box = pygame.Rect(pos[0], pos[1], 20, 20)
    pygame.draw.rect(screen, WHITE, box, 2)
    if checked:
        pygame.draw.rect(screen, GREEN, box.inflate(-4, -4))

def draw_slider(x, y, value=0):
    rect = pygame.Rect(x, y, 200, 10)
    pygame.draw.rect(screen, GRAY, rect)
    handle_x = x + int(value / 255 * 200)
    pygame.draw.circle(screen, WHITE, (handle_x, y + 5), 8)
    return rect

def draw_color_preview(color, rect):
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, WHITE, rect, 2)

def draw_color_sliders(base_x, base_y, label_prefix="1", colors=None, color_index=0, color_list_name="SPECTROGRAM_COLORS"):
    for i, channel in enumerate(["R", "G", "B"]):
        draw_label(f"{channel}", (base_x, base_y + i * 35))
        slider_rect = draw_slider(base_x + 50, base_y + i * 35 + 5, value=colors[color_index][i] if colors else 0)
        draw_label(str(colors[color_index][i] if colors else 0), (base_x + 260, base_y + i * 35))
        # Store the slider info for interaction
        settings_ui[f'slider_{label_prefix}_{channel}'] = {
            'type': 'slider',
            'rect': slider_rect,
            'var_name': f'COLOR_SLIDER',
            'color_index': color_index,
            'color_comp': i,
            'min': 0,
            'max': 255,
            'color_list_name': color_list_name
        }

def draw_section(x, y, title, color_preview_color, active_var, gradient_var, colors, color_count_var):
    # Checkbox + Label
    draw_checkbox(globals()[active_var], (x, y))
    draw_label(title, (x + 30, y), bold=True)
    settings_ui[f'toggle_{active_var}'] = {'type': 'toggle', 'rect': pygame.Rect(x, y, 20, 20), 'var_name': active_var}

    # Gradient checkbox
    draw_checkbox(globals()[gradient_var], (x, y + 25))
    draw_label("Gradient", (x + 30, y + 25))
    settings_ui[f'toggle_{gradient_var}'] = {'type': 'toggle', 'rect': pygame.Rect(x, y + 25, 20, 20), 'var_name': gradient_var}

    # Buttons 1 2 3
    for i in range(1, 4):
        rect = pygame.Rect(x + 120 + (i - 1) * 40, y + 20, 35, 30)
        color = GREEN if globals()[color_count_var] == i else DARK_GRAY
        draw_button(str(i), rect, color=color)
        settings_ui[f'button_color_count_{color_count_var}_{i}'] = {'type': 'button_color_count', 'rect': rect, 'value': i, 'var_name': color_count_var}

    # Color sliders and previews
    color_list = globals()[colors]
    for i in range(globals()[color_count_var]):
        x_offset = 0
        if i == 1:
            x_offset = 360
        elif i == 2:
            x_offset = 720
        if len(color_list) > i:
            draw_color_sliders(x + x_offset, y + 60, f"{title} Color {i+1}", colors=color_list, color_index=i, color_list_name=colors)
            preview_rect = pygame.Rect(x + 300 + x_offset, y + 60, 40, 40)
            draw_color_preview(color_list[i], preview_rect)
            settings_ui[f'color_preview_{title}_{i}'] = {'type': 'color_preview', 'rect': preview_rect, 'color_list_name': colors, 'color_index': i}

# Settings Screen
def draw_settings_screen():
    global settings_ui, screen_size
    settings_ui = {}
    screen.fill(BACKGROUND_COLOR)

    # Top bar
    pygame.draw.rect(screen, GRAY, (0, 0, 1280, 30))
    draw_label("                                                                                                                                   Settings", (10, 5), bold=True)

    # Gain Factor
    draw_label("Gain Factor", (520, 40))
    gain_slider_rect = draw_slider(620, 45, value=int(GAIN_FACTOR * (255/20)))
    draw_label(str(GAIN_FACTOR), (840, 40))
    settings_ui['slider_GAIN_FACTOR'] = {'type': 'slider', 'rect': gain_slider_rect, 'var_name': 'GAIN_FACTOR', 'min': 1, 'max': 20}

    # Horizontal lines
    pygame.draw.line(screen, WHITE, (0, 114), (1280, 114), 1)
    pygame.draw.line(screen, WHITE, (0, 240), (1280, 240), 1)
    pygame.draw.line(screen, WHITE, (0, 420), (1280, 420), 1)
    pygame.draw.line(screen, WHITE, (0, 620), (1280, 620), 1)

    # Vertical lines
    pygame.draw.line(screen, WHITE, (370, 114), (370, 620), 1)
    pygame.draw.line(screen, WHITE, (730, 114), (730, 620), 1)

    # Sections
    draw_section(20, 60, "Spectrum", BLUE, "SPECTRUM_ACTIVE", "SPECTRUM_GRADIENT_ACTIVE", "SPECTRUM_COLORS", "SPECTRUM_COLOR_COUNT")
    draw_section(20, 250, "Oscilloscope", GREEN, "OSCILLOSCOPE_ACTIVE", "OSCILLOSCOPE_GRADIENT_ACTIVE", "OSCILLOSCOPE_COLORS", "OSCILLOSCOPE_COLOR_COUNT")
    draw_section(20, 440, "Spectrogram", YELLOW, "SPECTROGRAM_ACTIVE", "SPECTROGRAM_GRADIENT_ACTIVE", "SPECTROGRAM_COLORS", "SPECTROGRAM_COLOR_COUNT")


    # --- Draw Color Theme Selector ---
    theme_box_x = 10
    theme_box_y = 610
    draw_label("Color Themes", (theme_box_x, theme_box_y - 25), bold=True)
    draw_label(f"Selected: {SELECTED_SPECTRUM_THEME}", (theme_box_x + 130, theme_box_y - 25), bold=True)
    
    button_width = 110
    button_height = 30
    
    # Draw preset theme buttons
    for i, theme_name in enumerate(SPECTRUM_THEMES):
        x_offset = i * (button_width + 10)
        button_rect = pygame.Rect(theme_box_x + x_offset, theme_box_y, button_width, button_height)
        color = GREEN if SELECTED_SPECTRUM_THEME == theme_name else DARK_GRAY
        draw_button(theme_name, button_rect, color=color)
        settings_ui[f'theme_button_{theme_name}'] = {'type': 'theme_button', 'rect': button_rect, 'theme': theme_name}



    # Bottom buttons
    buttons = ["Back to Main", "Save Settings", "Load Settings", "Toggle Fullscreen (F11)", "Exit"]
    actions = ["main", "save_settings", "load_settings", "toggle_fullscreen", "exit"]
    for i, text in enumerate(buttons):
        rect = pygame.Rect(20 + i * 250, 650, 220, 40)
        draw_button(text, rect)
        settings_ui[f'button_{actions[i]}'] = {'type': 'button', 'rect': rect, 'action': actions[i]}

# --- Handle_Settings_Click --- #

def handle_settings_click(pos):
    global app_state, slider_dragging, GAIN_FACTOR, OSCILLOSCOPE_ACTIVE, SPECTRUM_ACTIVE, SPECTROGRAM_ACTIVE, \
           OSCILLOSCOPE_COLOR_COUNT, SPECTRUM_COLOR_COUNT, SPECTROGRAM_COLOR_COUNT, OSCILLOSCOPE_GRADIENT_ACTIVE, SPECTRUM_GRADIENT_ACTIVE, SPECTROGRAM_GRADIENT_ACTIVE

    for key, ui_element in settings_ui.items():
        if ui_element['rect'].collidepoint(pos):

            # --- Check for theme button clicks ---
            if ui_element['type'] == 'theme_button':
                theme_name = ui_element['theme']
                # Check if the theme is one of the fixed presets
                if theme_name in ["Fire", "Ice", "Melon", "Halloween", "Dracula", "Frog"]:
                    # Load the theme, but don't allow saving over it
                    # The apply_spectrum_theme function already handles this
                    apply_spectrum_theme(theme_name)
                    SELECTED_SPECTRUM_THEME = theme_name # Update the global variable
                else:
                    # For the "Custom" theme, allow full modification and saving
                    apply_spectrum_theme(theme_name)
                    SELECTED_SPECTRUM_THEME = theme_name
                return
            
            if ui_element['type'] == 'slider':
                slider_dragging = ui_element
                return
        
            if ui_element['type'] == 'button':
                action = ui_element['action']
                if action == 'main':
                    app_state = APP_STATE_MAIN
                elif action == 'save_settings':
                    save_settings()
                elif action == 'load_settings':
                    load_settings()
                    # We don't need to re-initialize the UI here since it's redrawn every frame
                elif action == 'toggle_fullscreen':
                    toggle_fullscreen()
                elif action == 'exit':
                    pygame.quit()
                    sys.exit()
                    
            if ui_element['type'] == 'toggle':
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
            
            if ui_element['type'] == 'button_color_count':
                var_name = ui_element['var_name']
                value = ui_element['value']
            
                if var_name == "SPECTRUM_COLOR_COUNT":
                    globals()[var_name] = value
                    if len(SPECTRUM_COLORS) < value:
                        for _ in range(value - len(SPECTRUM_COLORS)):
                            SPECTRUM_COLORS.append((255, 255, 255))
                    elif len(SPECTRUM_COLORS) > value:
                        SPECTRUM_COLORS[:] = SPECTRUM_COLORS[:value]
                elif var_name == "OSCILLOSCOPE_COLOR_COUNT":
                    globals()[var_name] = value
                    if len(OSCILLOSCOPE_COLORS) < value:
                        for _ in range(value - len(OSCILLOSCOPE_COLORS)):
                            OSCILLOSCOPE_COLORS.append((255, 255, 255))
                    elif len(OSCILLOSCOPE_COLORS) > value:
                        OSCILLOSCOPE_COLORS[:] = OSCILLOSCOPE_COLORS[:value]
                elif var_name == "SPECTROGRAM_COLOR_COUNT":
                    globals()[var_name] = value
                    if len(SPECTROGRAM_COLORS) < value:
                        for _ in range(value - len(SPECTROGRAM_COLORS)):
                            SPECTROGRAM_COLORS.append((255, 255, 255))
                    elif len(SPECTROGRAM_COLORS) > value:
                        SPECTROGRAM_COLORS[:] = SPECTROGRAM_COLORS[:value]

def handle_slider_drag(pos):
    global slider_dragging, GAIN_FACTOR
    if slider_dragging:
        x_norm = (pos[0] - slider_dragging['rect'].x) / slider_dragging['rect'].width
        x_norm = max(0.0, min(1.0, x_norm))
        
        var_name = slider_dragging['var_name']
        if var_name == "GAIN_FACTOR":
            value = slider_dragging['min'] + x_norm * (slider_dragging['max'] - slider_dragging['min'])
            GAIN_FACTOR = value
        elif var_name == 'COLOR_SLIDER':
            value = int(slider_dragging['min'] + x_norm * (slider_dragging['max'] - slider_dragging['min']))
            color_list_name = slider_dragging['color_list_name']
            color_list = globals()[color_list_name]
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


# --- Helper function for color strings ---
def parse_color_string(color_str):
    """Converts a string like '(255, 0, 0)' to a tuple (255, 0, 0)."""
    try:
        # Remove parentheses and split by comma
        color_values = color_str.strip('()').split(',')
        return tuple(int(c.strip()) for c in color_values)
    except (ValueError, IndexError):
        print(f"Error parsing color string: {color_str}. Using default color (0,0,0).")
        return (0, 0, 0)

# --- Apply Theme Function ---
def apply_spectrum_theme(theme_name):
    global SPECTRUM_COLORS, SPECTRUM_COLOR_COUNT, SPECTRUM_GRADIENT_ACTIVE, SELECTED_SPECTRUM_THEME, app_state
    
    if theme_name in config:
        theme_config = config[theme_name]
        try:
            SPECTRUM_COLOR_COUNT = theme_config.getint('spectrum_color_count')
            SPECTRUM_GRADIENT_ACTIVE = theme_config.getboolean('spectrum_gradient_active')
            
            new_colors = []
            for i in range(1, SPECTRUM_COLOR_COUNT + 1):
                color_str = theme_config.get(f'spectrum_color_{i}', fallback='(0,0,0)')
                new_colors.append(parse_color_string(color_str))
            
            SPECTRUM_COLORS = new_colors
            SELECTED_SPECTRUM_THEME = theme_name
            
            if 'draw_settings_screen' in globals() and app_state == APP_STATE_SETTINGS:
                draw_settings_screen()
                pygame.display.flip()

        except configparser.Error as e:
            print(f"Error reading theme '{theme_name}': {e}")

# Initial call to load settings or set defaults
reset_default_settings()
load_settings()


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

                        elif event.key == pygame.K_ESCAPE:
                            if app_state == APP_STATE_SETTINGS:
                                app_state = APP_STATE_MAIN

                
                if app_state == APP_STATE_MAIN:
                    screen.fill(BACKGROUND_COLOR)
                    
                    if 'audio_data_buffer' in globals() and audio_data_buffer is not None:
                        # Process audio data for visualizations
                        cleaned_audio_buffer = np.nan_to_num(audio_data_buffer, copy=True, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

                        # Spectrogram
                        if SPECTROGRAM_ACTIVE:
                            f, t_spec, Sxx = spectrogram(cleaned_audio_buffer, SAMPLING_RATE, nperseg=nperseg_setting, noverlap=noverlap_setting)
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
