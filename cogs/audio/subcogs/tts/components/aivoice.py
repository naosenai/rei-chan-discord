# This code is heavily modified from https://github.com/sinsen9000/A.I.VOICE_API_python
# A.I.VOICE Editor (v1.3.0以降) is required to be installed on the system.
# The API is not headless, so it requires the A.I.VOICE Editor to be running in the background.

import asyncio
import clr
import io
import json
import os
import sys
import tempfile
import time

# Ensure the path to the .NET assembly is added to the system path
sys.path.append("C:/Program Files/AI/AIVoice/AIVoiceEditor/")

from pydantic import BaseModel

# Add .NET assembly reference and import API components
clr.AddReference("AI.Talk.Editor.Api") # type: ignore
from AI.Talk.Editor.Api import TtsControl, HostStatus  # type: ignore

# API can only process one TTS request at the same time
tts_lock = asyncio.Lock()



class VoiceArgs(BaseModel):
    target_text: str
    name: str
    volume: float
    speed: float
    pitch: float
    intonation: float
    angry: float
    pleasure: float
    sad: float

class AIVoice(TtsControl):
    def __init__(self):
        if not os.path.isfile('C:/Program Files/AI/AIVoice/AIVoiceEditor/AI.Talk.Editor.Api.dll'):
            print("A.I.VOICE Editor (v1.3.0以降) がインストールされていません。")
            return False
        super().__init__()
        self.host_name = ""
        self.voices = []
        self.start_api()
        self.disconnect()

    def start_api(self):
        self.host_name = self.GetAvailableHostNames()[0]
        self.Initialize(self.host_name)
        self.StartHost()
        self.Connect()
        self.voices = [i for i in self.VoicePresetNames] # You can use self.VoiceNames to exclude presets

    def connect(self):
        if self.Status == HostStatus.NotRunning:
            self.start_api()
        else:
            self.Connect()

    def disconnect(self):
        if not self.Status == HostStatus.NotRunning:
            self.Disconnect()
        
    def set_preset(self, args):
        preset_param = json.loads(self.GetVoicePreset(args.name))
        preset_param["Volume"] = args.volume
        preset_param["Speed"] = args.speed
        preset_param["Pitch"] = args.pitch
        preset_param["PitchRange"] = args.intonation

        styles = preset_param.get("Styles", [])
        if len(styles) > 0: styles[0]["Value"] = args.pleasure
        if len(styles) > 1: styles[1]["Value"] = args.angry
        if len(styles) > 2: styles[2]["Value"] = args.sad

        self.SetVoicePreset(json.dumps(preset_param))
        self.Text = args.target_text
        self.CurrentVoicePresetName = args.name

    def get_file(self, args: VoiceArgs) -> io.BytesIO:
        self.set_preset(args)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            temp_path = tmpfile.name
        self.SaveAudioToFile(temp_path)
        with open(temp_path, "rb") as f:
            audio_stream = io.BytesIO(f.read())
        os.remove(temp_path)
        audio_stream.seek(0)
        return audio_stream



async def make_tts(instance: AIVoice, voice:str, sentence:str, pitch="100", speed="100", intonation="100", volume="100", param={"activation": False}):
    instance.connect()
    pitch = str(min(max(int(pitch), 50), 200))
    speed = str(min(max(int(speed), 50), 400))
    name = voice if voice in instance.voices else instance.voices[0] # Default to first voice if not found

    voice_args = VoiceArgs(
        target_text=sentence,
        name=name,
        volume=int(volume) / 100,
        speed=int(speed) / 100,
        pitch=int(pitch) / 100,
        intonation=int(intonation) / 100,
        angry=0,
        pleasure=0,
        sad=0
    )
    if param.get("activation"): # Emotion values are unused in the current implementation, but can be set for future use
        emo_value = param.get("value", 0)
        emo_type = param.get("emo")
        if emo_type == "yorokobi":
            voice_args.pleasure = emo_value
        elif emo_type == "ikari":
            voice_args.angry = emo_value
        elif emo_type == "aware":
            voice_args.sad = emo_value

    async with tts_lock:
        for attempt in range(3):
            try:
                audio_stream = instance.get_file(voice_args)
                break
            except Exception as e:
                if "host program is busy" in str(e).lower():
                    time.sleep(0.2)
                else:
                    raise e
        else:
            if attempt == 2:
                return False
    instance.disconnect()
    return audio_stream