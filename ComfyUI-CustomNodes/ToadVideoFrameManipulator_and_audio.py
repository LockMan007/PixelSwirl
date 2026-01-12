import numpy as np
import torch
import random
import cv2

class ToadVideoFrameManipulator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "audio": ("AUDIO",),
                
                # Video settings
                "color_to_bw_on": ("BOOLEAN", {"default": True}),
                "color_to_bw_probability": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "bw_duration": ("INT", {"default": 5, "min": 1}),
                "flip_on": ("BOOLEAN", {"default": True}),
                "flip_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "flip_duration": ("INT", {"default": 3, "min": 1}),
                "mirror_on": ("BOOLEAN", {"default": True}),
                "mirror_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "mirror_duration": ("INT", {"default": 4, "min": 1}),
                "saturation_on": ("BOOLEAN", {"default": True}),
                "saturation_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "saturation_min": ("FLOAT", {"default": 0.5, "min": 0.00, "max": 5.0, "step": 0.01}),
                "saturation_max": ("FLOAT", {"default": 5.0, "min": 0.00, "max": 5.0, "step": 0.01}),
                "saturation_duration": ("INT", {"default": 5, "min": 1}),
                "tearing_on": ("BOOLEAN", {"default": True}),
                "tearing_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "tearing_duration": ("INT", {"default": 5, "min": 1}),
                "melting_on": ("BOOLEAN", {"default": True}),
                "melting_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "melting_duration": ("INT", {"default": 5, "min": 1}),
                "tiling_on": ("BOOLEAN", {"default": True}),
                "tiling_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "tiling_factor": ("INT", {"default": 4, "min": 2, "max": 16}),
                "color_separation_on": ("BOOLEAN", {"default": True}),
                "color_separation_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "color_separation_distance": ("INT", {"default": 50, "min": 5, "max": 1000}),
                "pixelate_on": ("BOOLEAN", {"default": True}),
                "pixelate_probability": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.01}),
                "pixelate_factor": ("INT", {"default": 4, "min": 2, "max": 50}),

                # Time-Based Audio settings
                "audio_stutter_on": ("BOOLEAN", {"default": True}),
                "audio_stutter_probability": ("FLOAT", {"default": 0.05, "min": 0.0, "max": 1.0, "step": 0.01}),
                "audio_stutter_clip": ("FLOAT", {"default": 0.1, "min": 0.01, "max": 10.0, "step": 0.01}),
                "audio_stutter_duration": ("FLOAT", {"default": 0.5, "min": 0.01, "max": 10.0, "step": 0.01}),
                
                "audio_reverse_on": ("BOOLEAN", {"default": True}),
                "audio_reverse_probability": ("FLOAT", {"default": 0.02, "min": 0.0, "max": 1.0, "step": 0.01}),
                "audio_reverse_clip": ("FLOAT", {"default": 0.5, "min": 0.01, "max": 10.0, "step": 0.01}),
                "audio_reverse_duration": ("FLOAT", {"default": 0.5, "min": 0.01, "max": 10.0, "step": 0.01}),
            },
            "optional": {
                "video_info": ("VHS_VIDEOINFO",),
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT")
    RETURN_NAMES = ("images", "audio", "framerate")
    FUNCTION = "process_frames"
    CATEGORY = "Video Manipulation"

    def __init__(self):
        self.bw_counter = 0
        self.flip_counter = 0
        self.mirror_counter = 0
        self.saturation_counter = 0
        self.tearing_counter = 0
        self.melting_counter = 0
        self.pixelate_counter = 0
        # Persistent audio state
        self.audio_stutter_remaining = 0
        self.audio_stutter_chunk = None
        self.audio_reverse_remaining = 0
        self.audio_reverse_buffer = None

    def process_frames(self, images, audio, **kwargs):
        device = images.device
        video_info = kwargs.get("video_info", None)
        fps = float(video_info["fps"]) if video_info and "fps" in video_info else 30.0

        waveform = audio["waveform"].clone().to(device).float()
        sample_rate = audio["sample_rate"]
        
        # Standardize waveform shape to [channels, samples]
        if len(waveform.shape) == 3:
            waveform = waveform[0]
            
        num_channels, total_samples = waveform.shape
        batch_size = images.shape[0]
        samples_per_frame = int(total_samples // batch_size)
        output_images = torch.zeros_like(images)

        for i in range(batch_size):
            frame = (images[i].cpu().numpy() * 255).astype(np.uint8)
            start_sample = i * samples_per_frame
            end_sample = min(start_sample + samples_per_frame, total_samples)
            current_frame_size = end_sample - start_sample
            audio_segment = waveform[:, start_sample:end_sample]

            # --- VIDEO EFFECTS ---
            if kwargs.get("color_to_bw_on"):
                if self.bw_counter > 0:
                    frame = cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
                    self.bw_counter -= 1
                elif random.random() < kwargs.get("color_to_bw_probability"):
                    self.bw_counter = kwargs.get("bw_duration")

            if kwargs.get("flip_on"):
                if self.flip_counter > 0:
                    frame = cv2.flip(frame, 0); self.flip_counter -= 1
                elif random.random() < kwargs.get("flip_probability"):
                    self.flip_counter = kwargs.get("flip_duration")

            if kwargs.get("mirror_on"):
                if self.mirror_counter > 0:
                    frame = cv2.flip(frame, 1); self.mirror_counter -= 1
                elif random.random() < kwargs.get("mirror_probability"):
                    self.mirror_counter = kwargs.get("mirror_duration")

            if kwargs.get("saturation_on"):
                if self.saturation_counter > 0:
                    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
                    s_change = random.uniform(kwargs.get("saturation_min"), kwargs.get("saturation_max"))
                    hsv[..., 1] = np.clip(hsv[..., 1] * s_change, 0, 255)
                    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB); self.saturation_counter -= 1
                elif random.random() < kwargs.get("saturation_probability"):
                    self.saturation_counter = kwargs.get("saturation_duration")

            if kwargs.get("tearing_on"):
                if self.tearing_counter > 0 or random.random() < kwargs.get("tearing_probability"):
                    line = random.randint(0, frame.shape[0] - 1)
                    frame[line:] = np.roll(frame[line:], random.randint(-15, 15), axis=1)
                    self.tearing_counter = self.tearing_counter - 1 if self.tearing_counter > 0 else kwargs.get("tearing_duration")

            if kwargs.get("melting_on"):
                if self.melting_counter > 0 or random.random() < kwargs.get("melting_probability"):
                    strips = random.randint(2, 6)
                    w = frame.shape[1] // strips
                    for j in range(strips):
                        frame[:, j*w:(j+1)*w] = np.roll(frame[:, j*w:(j+1)*w], random.randint(5, 20), axis=0)
                    self.melting_counter = self.melting_counter - 1 if self.melting_counter > 0 else kwargs.get("melting_duration")

            if kwargs.get("tiling_on") and random.random() < kwargs.get("tiling_probability"):
                f = random.randint(2, kwargs.get("tiling_factor"))
                th, tw = frame.shape[0] // f, frame.shape[1] // f
                tile = cv2.resize(frame, (tw, th))
                frame = cv2.resize(np.tile(tile, (f, f, 1)), (frame.shape[1], frame.shape[0]))

            if kwargs.get("color_separation_on") and random.random() < kwargs.get("color_separation_probability"):
                dist = kwargs.get("color_separation_distance")
                b, g, r = cv2.split(frame)
                frame = cv2.merge([np.roll(b, dist, axis=1), g, np.roll(r, -dist, axis=1)])

            if kwargs.get("pixelate_on"):
                pf = kwargs.get("pixelate_factor")
                if self.pixelate_counter > 0:
                    small = cv2.resize(frame, (max(1, frame.shape[1] // pf), max(1, frame.shape[0] // pf)), interpolation=cv2.INTER_NEAREST)
                    frame = cv2.resize(small, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
                    self.pixelate_counter -= 1
                elif random.random() < kwargs.get("pixelate_probability"):
                    self.pixelate_counter = pf

            # --- AUDIO EFFECTS ---
            
            # 1. Stutter Logic (With Channel Mismatch Fix)
            if kwargs.get("audio_stutter_on"):
                if self.audio_stutter_remaining <= 0:
                    if random.random() < kwargs.get("audio_stutter_probability"):
                        clip_s = int(kwargs.get("audio_stutter_clip") * sample_rate)
                        self.audio_stutter_remaining = int(kwargs.get("audio_stutter_duration") * sample_rate)
                        c_start = max(0, start_sample - clip_s)
                        self.audio_stutter_chunk = waveform[:, c_start:max(c_start + 1, start_sample)]
                
                if self.audio_stutter_remaining > 0 and self.audio_stutter_chunk is not None:
                    # Fix channel mismatch if user switched videos
                    if self.audio_stutter_chunk.shape[0] != num_channels:
                        self.audio_stutter_chunk = self.audio_stutter_chunk[0:1].repeat(num_channels, 1)

                    cl = self.audio_stutter_chunk.shape[1]
                    waveform[:, start_sample:end_sample] = self.audio_stutter_chunk.repeat(1, (current_frame_size // cl) + 1)[:, :current_frame_size]
                    self.audio_stutter_remaining -= current_frame_size

            # 2. Reverse Logic (With Channel Mismatch Fix)
            if kwargs.get("audio_reverse_on"):
                if self.audio_reverse_remaining <= 0:
                    if random.random() < kwargs.get("audio_reverse_probability"):
                        rev_clip_s = int(kwargs.get("audio_reverse_clip") * sample_rate)
                        self.audio_reverse_remaining = int(kwargs.get("audio_reverse_duration") * sample_rate)
                        c_start = max(0, start_sample - rev_clip_s)
                        self.audio_reverse_buffer = torch.flip(waveform[:, c_start:max(c_start + 1, start_sample)], [1])
                
                if self.audio_reverse_remaining > 0 and self.audio_reverse_buffer is not None:
                    # Fix channel mismatch if user switched videos
                    if self.audio_reverse_buffer.shape[0] != num_channels:
                        self.audio_reverse_buffer = self.audio_reverse_buffer[0:1].repeat(num_channels, 1)

                    rl = self.audio_reverse_buffer.shape[1]
                    waveform[:, start_sample:end_sample] = self.audio_reverse_buffer.repeat(1, (current_frame_size // rl) + 1)[:, :current_frame_size]
                    self.audio_reverse_remaining -= current_frame_size

            output_images[i] = torch.from_numpy(frame.astype(np.float32) / 255.0).to(device)

        return (output_images, {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}, fps)

NODE_CLASS_MAPPINGS = {"ToadVideoFrameManipulator": ToadVideoFrameManipulator}
NODE_DISPLAY_NAME_MAPPINGS = {"ToadVideoFrameManipulator": "Toad Video Frame Manipulator"}