from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa

# load model and processor with specific cache directory
processor = WhisperProcessor.from_pretrained("openai/whisper-small", cache_dir="cache")
model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-small", cache_dir="cache").to("cuda")
model.config.forced_decoder_ids = None

# load your local audio file
audio_path = 'test.wav'
audio_array, sr_original = librosa.load(audio_path, sr=None)  # Load the file as is with its native sampling rate

# Resample the audio to 16000 Hz if necessary
if sr_original != 16000:
    audio_array = librosa.resample(audio_array, orig_sr=sr_original, target_sr=16000)

# process your audio sample
input_features = processor(audio_array, sampling_rate=16000, return_tensors="pt").input_features.to("cuda")

# generate token ids
predicted_ids = model.generate(input_features)

# decode token ids to text, ensuring skip_special_tokens is set to True to ignore special tokens in output
transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)
print(transcription)
