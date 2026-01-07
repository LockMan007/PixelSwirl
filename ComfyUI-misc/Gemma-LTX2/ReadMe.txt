Downlaod the missing files from here:
https://huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized/tree/main

To make it easier, i have made a zip of the files below called:
Gemma-missing the 32mb Tokenizer.json and large model files.zip

The zip includes:

README.md
added_tokens.json
chat_template.json
config.json
generation_config.json
model.safetensors.index.json
preprocessor_config.json
processor_config.json
special_tokens_map.json
tokenizer.model
tokenizer_config.json

################################################
HOWEVER IT IS MISSING THE LARGE 32 Megabyte tokenizer.json and file and the model file(s)
Download the big files from: https://huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized/tree/main
or you can download all the files 1 by one, I'm just trying to make it easier, because it is dumb to click several times to download many 1KB files.
################################################

MISSING:
tokenizer.json
model-00001-of-00005.safetensors
model-00002-of-00005.safetensors
model-00003-of-00005.safetensors
model-00004-of-00005.safetensors
model-00005-of-00005.safetensors

Also doesn't include
gemma_3_12B_it_fp8_e4m3fn.safetensors
