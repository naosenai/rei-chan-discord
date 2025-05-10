import os
import io

from pydub import AudioSegment

# Set converter path for pydub
AudioSegment.converter = os.path.abspath("tools/ffmpeg.exe")

def convert_filetype(audio_stream: io.BytesIO, filelimit) -> io.BytesIO:
    audio_stream.seek(0, io.SEEK_END)
    filesize = audio_stream.tell()
    audio_stream.seek(0)

    if filesize < filelimit:
        return audio_stream, "wav"

    wav_audio = AudioSegment.from_wav(audio_stream)
    mp3_stream = io.BytesIO()
    wav_audio.export(mp3_stream, format="mp3", bitrate="128k")
    mp3_stream.seek(0)

    if mp3_stream.getbuffer().nbytes < filelimit:
        return mp3_stream, "mp3"
    return False
    
