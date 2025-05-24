import os
import io
import asyncio

from typing import Literal
from pydub import AudioSegment
AudioSegment.converter = os.path.abspath("tools/ffmpeg.exe")

from .aivoice import AIVoice


class AIVoiceManager:
    def __init__(self):
        self._aivoice: AIVoice
        self._ready = asyncio.Event()
        self._init_task = asyncio.create_task(self._initialize())

    async def _initialize(self):
        loop = asyncio.get_event_loop()
        self._aivoice = await loop.run_in_executor(None, AIVoice)
        self._ready.set()
        print("AIVoice initialized.")

    async def get_instance(self):
        await self._ready.wait()
        return self._aivoice



def convert_filetype(audio_stream: io.BytesIO, filelimit) -> dict[str, io.BytesIO | str] | Literal[False]:
    audio_stream.seek(0, io.SEEK_END)
    filesize = audio_stream.tell()
    audio_stream.seek(0)

    if filesize < filelimit:
        return {"stream": audio_stream, "ext": "wav"}

    wav_audio = AudioSegment.from_wav(audio_stream)
    mp3_stream = io.BytesIO()
    wav_audio.export(mp3_stream, format="mp3", bitrate="128k")
    mp3_stream.seek(0)

    if mp3_stream.getbuffer().nbytes < filelimit:
        return {"stream": mp3_stream, "ext": "mp3"}
    return False



aivoice_manager = AIVoiceManager()
    
