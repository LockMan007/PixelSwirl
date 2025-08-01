import sounddevice as sd
import sys

# Replace with the index you want to investigate (22 for "What U Hear")
DEVICE_INDEX = 22

try:
    print("Sounddevice version:", sd.__version__)
    print("PortAudio version:", sd.get_portaudio_version())

    # Get detailed device info
    device_info = sd.query_devices(DEVICE_INDEX, 'input')
    print(f"\n--- Detailed Info for Device {DEVICE_INDEX}: {device_info['name']} ---")
    print(f"Host API: {device_info['hostapi']}")
    print(f"Max Input Channels: {device_info['max_input_channels']}")
    print(f"Default Sample Rate: {device_info['default_samplerate']}")
    print(f"High Input Latency: {device_info['default_high_input_latency']}")
    print(f"Low Input Latency: {device_info['default_low_input_latency']}")

    # Attempt to find supported standard sample rates
    print("\nChecking common sample rates for compatibility:")
    common_rates = [44100, 48000, 96000, 192000]
    for rate in common_rates:
        try:
            # Test if the device can open an input stream at this rate
            # This will raise an error if not supported
            with sd.InputStream(samplerate=rate, channels=2, device=DEVICE_INDEX, callback=lambda *args: None, blocksize=0):
                print(f"  Rate {rate} Hz: SUPPORTED")
        except Exception as e:
            print(f"  Rate {rate} Hz: NOT SUPPORTED ({e})")

except Exception as e:
    print(f"\nAn error occurred: {e}", file=sys.stderr)

input("\nPress Enter to exit...")