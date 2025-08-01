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
COLOR_MODE = 1

# --- Load Settings ---
def load_settings():
    global GAIN_FACTOR
    global COLOR_MODE

    if os.path.exists(SETTINGS_FILE):
        try:
            config.read(SETTINGS_FILE)
            if 'SpectrumAnalyzer' in config:
                GAIN_FACTOR = float(config['SpectrumAnalyzer'].get('gain_factor', GAIN_FACTOR))
                COLOR_MODE = int(config['SpectrumAnalyzer'].get('color_mode', COLOR_MODE))
                print(f"Settings loaded from {SETTINGS_FILE}: Gain={GAIN_FACTOR}, Color Mode={COLOR_MODE}")
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
    GAIN_FACTOR = 5.0
    COLOR_MODE = 1

# Initial call to load settings or set defaults
reset_default_settings()
load_settings()

# --- Pygame Setup ---
INITIAL_SCREEN_WIDTH = 800
INITIAL_SCREEN_HEIGHT = 400

# NEW: Desired number of bars when the window is at INITIAL_SCREEN_WIDTH
# This helps maintain a consistent visual density regardless of window size.
TARGET_BAR_COUNT = 60 # You can adjust this number based on preference

pygame.init()

screen = pygame.display.set_mode((INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
pygame.display.set_caption("Spectrum Analyzer")
clock = pygame.time.Clock()

# Current screen dimensions (will change with resize/fullscreen)
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

# --- Menu Click Handler ---
def handle_menu_click(mouse_pos):
    global MENU_ACTIVE
    global GAIN_FACTOR
    global COLOR_MODE
    global running

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
    # BAR_WIDTH and BAR_SPACING will now be dynamically calculated inside the loop,
    # so they don't need to be global here for modification.

    is_fullscreen = False
    
    try:
        with sd.InputStream(samplerate=SAMPLING_RATE, channels=2, callback=audio_callback, blocksize=CHUNK_SIZE, device=DEVICE_ID):
            print(f"Listening to device index {DEVICE_ID} ('What U Hear')... Sample Rate: {SAMPLING_RATE} Hz")
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 3: # Right-click
                            MENU_ACTIVE = not MENU_ACTIVE
                            MENU_X, MENU_Y = event.pos
                        elif event.button == 1: # Left-click
                            if MENU_ACTIVE:
                                handle_menu_click(event.pos)
                            else:
                                MENU_ACTIVE = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_f11 or (event.key == pygame.K_RETURN and pygame.key.get_mods() & pygame.KMOD_ALT):
                            is_fullscreen = not is_fullscreen
                            if is_fullscreen:
                                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.SCALED | pygame.RESIZABLE)
                            else:
                                screen = pygame.display.set_mode((INITIAL_SCREEN_WIDTH, INITIAL_SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
                            SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
                            print(f"Window resized to: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                    elif event.type == pygame.VIDEORESIZE:
                        SCREEN_WIDTH, SCREEN_HEIGHT = event.size
                        print(f"Window resized to: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

                screen.fill((0, 0, 0))

                if 'audio_data_buffer' in globals() and audio_data_buffer is not None:
                    N = len(audio_data_buffer)
                    yf = fft(audio_data_buffer * np.hanning(N))
                    magnitudes = 2.0/N * np.abs(yf[0:N//2])

                    # NEW: Calculate BAR_WIDTH and BAR_SPACING dynamically
                    # Ensure at least 1 bar if screen is very small
                    BAR_WIDTH = max(1, int(SCREEN_WIDTH / (TARGET_BAR_COUNT * 1.5))) # Adjust 1.5 for desired spacing relative to width
                    BAR_SPACING = max(1, int(BAR_WIDTH * 0.2)) # A small spacing, e.g., 20% of bar width
                    
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

                        bar_height = int(bar_magnitude * (SCREEN_HEIGHT / 2) * GAIN_FACTOR)
                        if bar_height > SCREEN_HEIGHT:
                            bar_height = SCREEN_HEIGHT
                        elif bar_height < 0:
                            bar_height = 0

                        x = i * (BAR_WIDTH + BAR_SPACING)
                        y = SCREEN_HEIGHT - bar_height

                        if COLOR_MODE == 1:
                            pygame.draw.rect(screen, (0, 255, 0), (x, y, BAR_WIDTH, bar_height))
                        elif COLOR_MODE == 2:
                            for h_pixel in range(bar_height):
                                percentage = h_pixel / bar_height
                                color = get_gradient_color(percentage)
                                pygame.draw.rect(screen, color, (x, SCREEN_HEIGHT - 1 - h_pixel, BAR_WIDTH, 1))

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
    main()