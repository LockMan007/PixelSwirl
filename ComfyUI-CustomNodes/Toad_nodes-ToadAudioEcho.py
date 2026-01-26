import numpy as np
import torch
from pydub import AudioSegment

class ToadAudioEcho:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "enable_effects": ("BOOLEAN", {"default": True}),
                "echo_delay_duration": ("FLOAT", {"default": 500.0, "min": 0.0, "max": 5000.0, "step": 10.0}),
                "echo_volume_reduction": ("FLOAT", {"default": 6.0, "min": 0.0, "max": 60.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "apply_echo"

    def apply_echo(self, audio, enable_effects, echo_delay_duration, echo_volume_reduction):
        # Validate input audio
        if audio is None or 'waveform' not in audio or 'sample_rate' not in audio:
            raise ValueError("Invalid audio input")

        waveform, sample_rate = audio['waveform'], audio['sample_rate']
        audio_np = waveform.cpu().numpy().squeeze(0).squeeze(0)  # Shape: (num_samples,)

        # Convert numpy array to AudioSegment
        audio_segment = AudioSegment(
            audio_np.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,  # Assuming 16-bit audio (2 bytes per sample)
            channels=1,
        )

        print(f"Input audio range: {audio_np.min()} to {audio_np.max()}")

        if not enable_effects:
            # Return unprocessed audio
            return ({"waveform": waveform, "sample_rate": sample_rate},)

        # Apply echo effect
        echo_signal = self.create_echo(audio_segment, echo_delay_duration, echo_volume_reduction)

        # Combine original and echo
        output_audio = audio_segment.overlay(echo_signal)

        # Convert back to numpy array
        output_audio_np = np.array(output_audio.get_array_of_samples(), dtype=np.int16)

        print(f"Output audio range before normalization: {output_audio_np.min()} to {output_audio_np.max()}")

        # Normalize to float32 (-1.0 to 1.0)
        output_audio_np = output_audio_np.astype(np.float32) / 32768.0
        output_audio_np = np.clip(output_audio_np, -1.0, 1.0)  # Ensure valid range

        print(f"Output audio range after normalization: {output_audio_np.min()} to {output_audio_np.max()}")

        # Convert to PyTorch tensor
        output_audio_tensor = torch.from_numpy(output_audio_np).to(waveform.device).unsqueeze(0).unsqueeze(0)

        return ({"waveform": output_audio_tensor, "sample_rate": sample_rate},)

    def create_echo(self, audio_segment, echo_delay_duration, echo_volume_reduction):
        # Add silence for delay
        delay = AudioSegment.silent(duration=echo_delay_duration)  # Adjustable delay duration

        # Create echo with reduced volume (-echo_volume_reduction dB for each repetition)
        echo = (audio_segment - echo_volume_reduction).overlay(delay)
        echo = (echo - echo_volume_reduction).overlay(delay * 2)  # Add another layer with further reduced volume
        return echo

NODE_CLASS_MAPPINGS = {
    "ToadAudioEcho": ToadAudioEcho,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ToadAudioEcho": "Toad nodes: Toad Audio Echo",
}
