import wave
import os


def convert_rb_to_wav(data, output_path):
    num_channels = 1
    sample_width = 2
    frame_rate = 16000
    num_frames = len(data) // sample_width

    with wave.open('output.wav', 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(frame_rate)
        wav_file.setnframes(num_frames)
        wav_file.writeframes(data)

    return os.path.abspath(output_path)

