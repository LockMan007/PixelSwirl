import torchaudio
import folder_paths
import os

class Load_Audio_From_Save_Node:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_filepath": ("STRING",),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio_out",)
    FUNCTION = "load_audio"
    CATEGORY = "Audio Processing"

    def __init__(self):
        pass

    def load_audio(self, audio_filepath):
        # Load the audio file
        audio_path = folder_paths.get_annotated_filepath(audio_filepath)
        waveform, sample_rate = torchaudio.load(audio_path)
        audio_data = {
            "waveform": waveform.unsqueeze(0),
            "sample_rate": sample_rate
        }
        return (audio_data,)

NODE_CLASS_MAPPINGS = {
    "Load_Audio_From_Save_Node": Load_Audio_From_Save_Node,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Load_Audio_From_Save_Node": "Toad nodes: Load Audio from Save Node",
}
