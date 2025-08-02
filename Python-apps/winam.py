import sounddevice as sd
import numpy as np
from scipy.fftpack import fft
import pygame
import configparser
import os
import sys

# --- Configuration ---
CHUNK_SIZE = 1024
SAMPLING_RATE = 48000
DEVICE_ID = 22

# --- Settings File ---
SETTINGS_FILE = 'settings.ini'
config = configparser.ConfigParser()

# --- Global Variables for Settings ---
GAIN_FACTOR = 5.0
COLOR_MODE = 2
OSCILLOSCOPE_ACTIVE = True
SPECTRUM_ACTIVE = True
DEBUG_LINE_ACTIVE = False
TARGET_BAR_COUNT = 60  # Desired number of bars to be displayed on screen.

# --- Load Settings ---
def load_settings():
    global GAIN_FACTOR
    global COLOR_MODE
    global OSCILLOSCOPE_ACTIVE
    global SPECTRUM_ACTIVE
    global DEBUG_LINE_ACTIVE

    if os.path.exists(SETTINGS_FILE):
        try:
            config.read(SETTINGS_FILE)
            if 'SpectrumAnalyzer' in config:
                GAIN_FACTOR = float(config['SpectrumAnalyzer'].get('gain_factor', GAIN_FACTOR))
                COLOR_MODE = int(config['SpectrumAnalyzer'].get('color_mode', COLOR_MODE))
                OSCILLOSCOPE_ACTIVE = config['SpectrumAnalyzer'].getboolean('oscilloscope_active', OSCILLOSCOPE_ACTIVE)
                SPECTRUM_ACTIVE = config['SpectrumAnalyzer'].getboolean('spectrum_active', SPECTRUM_ACTIVE)
                DEBUG_LINE_ACTIVE = config['SpectrumAnalyzer'].getboolean('debug_line_active', DEBUG_LINE_ACTIVE)
                print(f"Settings loaded from {SETTINGS_FILE}: Gain={GAIN_FACTOR}, Color Mode={COLOR_MODE}, Oscilloscope={OSCILLOSCOPE_ACTIVE}, Spectrum={SPECTRUM_ACTIVE}, Debug Line={DEBUG_LINE_ACTIVE}")
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
    config['SpectrumAnalyzer']['color_mode'] = str(COLOR_MODE)
    config['SpectrumAnalyzer']['oscilloscope_active'] = str(OSCILLOSCOPE_ACTIVE)
    config['SpectrumAnalyzer']['spectrum_active'] = str(SPECTRUM_ACTIVE)
    config['SpectrumAnalyzer']['debug_line_active'] = str(DEBUG_LINE_ACTIVE)
    try:
        with open(SETTINGS_FILE, 'w') as configfile:
            config.write(configfile)
        print(f"Settings saved to {SETTINGS_FILE}.")
    except Exception as e:
        print(f"Error saving {SETTINGS_FILE}: {e}", file=sys.stderr)

# --- Reset Default Settings ---
def reset_default_settings():
    global GAIN_FACTOR
    global COLOR_MODE
    global OSCILLOSCOPE_ACTIVE
    global SPECTRUM_ACTIVE
    global DEBUG_LINE_ACTIVE
    GAIN_FACTOR = 5.0
    COLOR_MODE = 1
    OSCILLOSCOPE_ACTIVE = False
    SPECTRUM_ACTIVE = True
    DEBUG_LINE_ACTIVE = False

# Initial call to load settings or set defaults
reset_default_settings()
load_settings()

# --- Pygame Setup ---
INITIAL_SCREEN_WIDTH = 800
INITIAL_SCREEN_HEIGHT = 400

pygame.init()

# The screen variable now holds a reference to the display surface.
# It is important to set this up correctly to handle resizing.
screen = pygame.display.set_mode((INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Spectrum Analyzer")
clock = pygame.time.Clock()

SCREEN_WIDTH, SCREEN_HEIGHT = INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT

# --- Audio Callback Function ---
def audio_callback(indata, frames, time, status):
    if status:
        pass
    global audio_data_buffer
    audio_data_buffer = indata.flatten()

# --- Color Gradient Function ---
def get_gradient_color(percentage):
    if percentage <= 0.5:
        val = percentage * 2
        r = int(255 * val)
        g = 255
        b = 0
    else:
        val = 1 - ((percentage - 0.5) * 2)
        r = 255
        g = int(255 * val)
        b = 0
    return (r, g, b)
    
# --- Oscilloscope Drawing Function ---
def draw_oscilloscope():
    if 'audio_data_buffer' in globals() and audio_data_buffer is not None and len(audio_data_buffer) > 0:
        current_width, current_height = screen.get_size()
        center_y = current_height / 2

        cleaned_audio_buffer = np.nan_to_num(audio_data_buffer, copy=True, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        max_abs_val = np.max(np.abs(cleaned_audio_buffer))
        
        if max_abs_val == 0:
            pygame.draw.line(screen, (0, 0, 255), (0, int(center_y)), (current_width, int(center_y)), 2)
            return
            
        scaling_factor = (current_height / 2.0) / max_abs_val * 0.9

        points = []
        for i in range(len(cleaned_audio_buffer)):
            x = i * current_width / len(cleaned_audio_buffer)
            y = center_y - cleaned_audio_buffer[i] * scaling_factor
            
            y_clamped = max(0, min(int(y), current_height))
            points.append((int(x), y_clamped))

        if len(points) > 1:
            pygame.draw.lines(screen, (0, 0, 255), False, points, 2)

# --- Right-Click Menu Variables ---
MENU_ACTIVE = False
MENU_X = 0
MENU_Y = 0
MENU_FONT = pygame.font.Font(None, 24)
MENU_OPTIONS = [
    {"text": "Gain +1", "action": "gain_up"},
    {"text": "Gain -1", "action": "gain_down"},
    {"text": "Color: Green", "action": "color_green"},
    {"text": "Color: Gradient", "action": "color_gradient"},
    {"text": "Toggle Spectrum", "action": "toggle_spectrum"},
    {"text": "Toggle Oscilloscope", "action": "toggle_oscilloscope"},
    {"text": "Toggle Debug Line", "action": "toggle_debug_line"},
    {"text": "Toggle Fullscreen", "action": "toggle_fullscreen"},
    {"text": "Save Settings", "action": "save_settings"},
    {"text": "Load Settings", "action": "load_settings"},
    {"text": "Exit", "action": "exit"}
]
MENU_ITEM_HEIGHT = 30
MENU_PADDING = 10
MENU_BACKGROUND_COLOR = (50, 50, 50)
MENU_TEXT_COLOR = (255, 255, 255)

# --- Menu Drawing Function ---
def draw_menu():
    if not MENU_ACTIVE:
        return

    max_text_width = max([MENU_FONT.size(option["text"])[0] for option in MENU_OPTIONS])
    menu_width = max_text_width + (2 * MENU_PADDING)
    menu_height = len(MENU_OPTIONS) * MENU_ITEM_HEIGHT + (2 * MENU_PADDING)

    draw_x = MENU_X
    draw_y = MENU_Y
    if draw_x + menu_width > SCREEN_WIDTH:
        draw_x = SCREEN_WIDTH - menu_width
    if draw_y + menu_height > SCREEN_HEIGHT:
        draw_y = SCREEN_HEIGHT - menu_height

    menu_rect = pygame.Rect(draw_x, draw_y, menu_width, menu_height)
    pygame.draw.rect(screen, MENU_BACKGROUND_COLOR, menu_rect)
    pygame.draw.rect(screen, (200, 200, 200), menu_rect, 1)

    for i, option in enumerate(MENU_OPTIONS):
        text_surface = MENU_FONT.render(option["text"], True, MENU_TEXT_COLOR)
        text_rect = text_surface.get_rect(midleft=(draw_x + MENU_PADDING, draw_y + MENU_PADDING + i * MENU_ITEM_HEIGHT + MENU_ITEM_HEIGHT / 2))
        screen.blit(text_surface, text_rect)

        option['rect'] = text_rect.inflate(MENU_PADDING*2, 0)
    
    # Store the final menu rect for click detection
    globals()['menu_rect'] = menu_rect


# --- Menu Click Handler ---
def handle_menu_click(mouse_pos):
    global MENU_ACTIVE
    global GAIN_FACTOR
    global COLOR_MODE
    global OSCILLOSCOPE_ACTIVE
    global SPECTRUM_ACTIVE
    global DEBUG_LINE_ACTIVE
    global running
    global is_fullscreen
    global screen
    global SCREEN_WIDTH, SCREEN_HEIGHT

    if not MENU_ACTIVE:
        return

    for option in MENU_OPTIONS:
        if 'rect' in option and option['rect'].collidepoint(mouse_pos):
            MENU_ACTIVE = False
            if option["action"] == "gain_up":
                GAIN_FACTOR += 1.0
                print(f"Gain increased to: {GAIN_FACTOR}")
            elif option["action"] == "gain_down":
                if GAIN_FACTOR > 1.0:
                    GAIN_FACTOR -= 1.0
                print(f"Gain decreased to: {GAIN_FACTOR}")
            elif option["action"] == "color_green":
                COLOR_MODE = 1
                print("Color mode set to: Green")
            elif option["action"] == "color_gradient":
                COLOR_MODE = 2
                print("Color mode set to: Gradient")
            elif option["action"] == "toggle_spectrum":
                SPECTRUM_ACTIVE = not SPECTRUM_ACTIVE
                print(f"Spectrum Analyzer is now {'ON' if SPECTRUM_ACTIVE else 'OFF'}.")
            elif option["action"] == "toggle_oscilloscope":
                OSCILLOSCOPE_ACTIVE = not OSCILLOSCOPE_ACTIVE
                print(f"Oscilloscope is now {'ON' if OSCILLOSCOPE_ACTIVE else 'OFF'}.")
            elif option["action"] == "toggle_debug_line":
                DEBUG_LINE_ACTIVE = not DEBUG_LINE_ACTIVE
                print(f"Debug line is now {'ON' if DEBUG_LINE_ACTIVE else 'OFF'}.")
            elif option["action"] == "toggle_fullscreen":
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.SCALED | pygame.RESIZABLE)
                else:
                    screen = pygame.display.set_mode((INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT), pygame.RESIZABLE)
                SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
                print(f"Window resized to: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
            elif option["action"] == "save_settings":
                save_settings()
                print("Settings saved.")
            elif option["action"] == "load_settings":
                load_settings()
                print("Settings loaded.")
            elif option["action"] == "exit":
                running = False
            return

# --- Main Loop ---
def main():
    global audio_data_buffer
    global MENU_ACTIVE
    global MENU_X
    global MENU_Y
    global running
    global SCREEN_WIDTH, SCREEN_HEIGHT
    global screen
    global OSCILLOSCOPE_ACTIVE
    global SPECTRUM_ACTIVE
    global is_fullscreen
    global DEBUG_LINE_ACTIVE
    global TARGET_BAR_COUNT
    global GAIN_FACTOR

    is_fullscreen = False
    
    # The screen variable now holds a reference to the display surface.
    screen = pygame.display.set_mode((INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT), pygame.RESIZABLE)
    
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
                            MENU_ACTIVE = not MENU_ACTIVE
                            MENU_X, MENU_Y = event.pos
                        elif event.button == 1:  # Left-click
                            if MENU_ACTIVE:
                                # Check if the click was inside the menu
                                if 'menu_rect' in globals() and globals()['menu_rect'].collidepoint(event.pos):
                                    handle_menu_click(event.pos)
                                else:
                                    MENU_ACTIVE = False # Clicked outside the menu, so close it
                    elif event.type == pygame.VIDEORESIZE:
                        SCREEN_WIDTH, SCREEN_HEIGHT = event.size
                        # Recreate the screen surface with the new size
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                        print(f"Window resized to: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

                screen.fill((0, 0, 0))

                if OSCILLOSCOPE_ACTIVE:
                    draw_oscilloscope()

                if DEBUG_LINE_ACTIVE:
                    pygame.draw.line(screen, (0, 255, 0), (0, SCREEN_HEIGHT - 1), (SCREEN_WIDTH, SCREEN_HEIGHT - 1), 1)

                # --- Spectrum Analyzer ---
                if SPECTRUM_ACTIVE and 'audio_data_buffer' in globals() and audio_data_buffer is not None:
                    N = len(audio_data_buffer)
                    yf = fft(audio_data_buffer * np.hanning(N))
                    magnitudes = 2.0/N * np.abs(yf[0:N//2])

                    BAR_WIDTH = max(1, int(SCREEN_WIDTH / (TARGET_BAR_COUNT * 1.5)))
                    BAR_SPACING = max(1, int(BAR_WIDTH * 0.2))
                    
                    num_bars = int(SCREEN_WIDTH / (BAR_WIDTH + BAR_SPACING))
                    if num_bars <= 0:
                        num_bars = 1

                    for i in range(num_bars):
                        freq_bin_start = int(i * (N / 2) / num_bars)
                        freq_bin_end = int((i + 1) * (N / 2) / num_bars)
                        
                        if freq_bin_start < len(magnitudes) and freq_bin_start < freq_bin_end:
                            bar_magnitude = np.max(magnitudes[freq_bin_start:freq_bin_end])
                        else:
                            bar_magnitude = 0.0

                        bar_height = int(np.power(bar_magnitude, 0.5) * SCREEN_HEIGHT * GAIN_FACTOR)
                        bar_height = max(0, min(bar_height, SCREEN_HEIGHT))

                        x = i * (BAR_WIDTH + BAR_SPACING)
                        y = SCREEN_HEIGHT - bar_height

                        if COLOR_MODE == 1:
                            pygame.draw.rect(screen, (0, 255, 0), (x, y, BAR_WIDTH, bar_height))
                        elif COLOR_MODE == 2:
                            for h_pixel in range(min(bar_height, SCREEN_HEIGHT)):
                                percentage = h_pixel / bar_height if bar_height else 0
                                color = get_gradient_color(percentage)
                                y_pos = SCREEN_HEIGHT - 1 - h_pixel
                                if y_pos >= 0:
                                    pygame.draw.rect(screen, color, (x, y_pos, BAR_WIDTH, 1))

                draw_menu()

                pygame.display.flip()
                clock.tick(60)

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        save_settings()
        pygame.quit()

if __name__ == "__main__":
    audio_data_buffer = None
    menu_rect = pygame.Rect(0, 0, 0, 0) # Initialize menu_rect
    main()
