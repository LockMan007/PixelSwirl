import torch
import torchaudio

class BatchAudiotoad:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {},
            "optional": {
                # We start with one, but the JS will add more
                "audio_0": ("AUDIO",),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "concat_audio"
    CATEGORY = "audio"

    def concat_audio(self, **kwargs):
        # 1. Filter out None and Sort by the number in 'audio_X'
        active_keys = sorted([k for k in kwargs.keys() if kwargs.get(k) is not None], 
                            key=lambda x: int(x.split('_')[1]))
        
        audio_list = [kwargs[k] for k in active_keys]

        if not audio_list:
            # Return an empty audio dict to prevent downstream crashes
            return ({"waveform": torch.zeros((1, 1, 0)), "sample_rate": 44100},)

        waveforms = [a["waveform"] for a in audio_list]
        sample_rates = [a["sample_rate"] for a in audio_list]

        # Concatenate on the last dimension (time/samples)
        combined_waveform = torch.cat(waveforms, dim=-1)

        # Return the combined waveform and use the sample rate of the first clip
        return ({"waveform": combined_waveform, "sample_rate": sample_rates[0]},)

NODE_CLASS_MAPPINGS = {
    "BatchAudiotoad": BatchAudiotoad
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchAudiotoad": "Batch_Audio_toad"
}