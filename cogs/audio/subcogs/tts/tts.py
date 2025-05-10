import os
import discord

from discord.ext import commands
from discord import app_commands
from datetime import datetime

from .components.helper_funcs import convert_filetype
from .components.aivoice import AIVoice, make_tts



class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aivoice = AIVoice()

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="tts", description="Convert text into a message using AIvoice! DO NOT SEND PRIVATE/SENSITIVE MESSAGES USING THIS!")
    @app_commands.describe(
        message="The message you want to convert", 
        voice="The voice you want to use (default: 足立 レイ)",
        interval="The interval, or pause length, between words (default: 100, 50-200)",
        speed="The speed of the voice (default: 100, 50-400)",
        intonation="The intonation, or emphasis, of the voice (default: 100)",
        volume="The volume of the voice (default: 100)"
        )
    async def tts(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        voice: str = "足立 レイ", 
        interval: int = 100, 
        speed: int = 100, 
        intonation: int = 100, 
        volume: int = 100
        ):
        await interaction.response.defer()  # Prevents timeout during generation

        allowed_users = set(map(int, os.getenv("ALLOWED_USERS", "").split(",")))
        allowed_guilds = set(map(int, os.getenv("ALLOWED_GUILDS", "").split(",")))
        filesize_limit = 8 * 1024 * 1024  # 8 MB in bytes, you can adjust if you have nitro

        if interaction.user.id in allowed_users: pass
        elif interaction.guild is None or interaction.guild.id not in allowed_guilds:
            await interaction.followup.send(
                content="Due to security concerns, this command has been restricted to only be used in my server (Check the bot bio) or by authorized individuals.",
                ephemeral=True
            )
            return

        audio_stream = await make_tts(
            instance=self.aivoice,
            voice=voice,
            sentence=message,
            interval=str(interval),
            speed=str(speed),
            intonation=str(intonation),
            volume=str(volume)
        )
        if audio_stream is False:
            await interaction.followup.send(
                content="The program is busy, try again later!",
                ephemeral=True
            )
            return
        
        audio_stream, ext = convert_filetype(audio_stream, filesize_limit)
        if audio_stream is False:
            await interaction.followup.send(
                content="The file is too large to send, please try again with a shorter message!",
                ephemeral=True
            )
            return
        
        await interaction.followup.send(
            content=f"Here is your TTS output using **{voice}**:",
            file=discord.File(audio_stream, filename=f"{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
        )

    @tts.autocomplete('voice')
    async def voice_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=v, value=v)
            for v in self.aivoice.voices if current.lower() in v.lower()
        ][:25]
        
        
async def setup(bot):
    await bot.add_cog(TTS(bot))