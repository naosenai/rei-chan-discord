import discord

from discord.ext import commands
from discord import app_commands

from .components.helper_funcs import aivoice_manager



class Voices(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aivoice = aivoice_manager

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="voices", description="Get a list of voices available for TTS.")
    async def voices(self, interaction: discord.Interaction):
        await interaction.response.defer()

        aivoice = await self.aivoice.get_instance()
        voice_list = aivoice.voices

        english_voices = [v for v in voice_list if "English" in v]
        chinese_voices = [v for v in voice_list if "Chinese" in v]
        japanese_voices = [v for v in voice_list if v not in english_voices + chinese_voices]

        embed = discord.Embed(
            title="Available Voices",
            color=discord.Color.orange()
        )

        if english_voices: embed.add_field(name="**English Voices**", value="\n".join(f"- {v}" for v in english_voices), inline=False)
        if chinese_voices: embed.add_field(name="**Chinese Voices**", value="\n".join(f"- {v}" for v in chinese_voices), inline=False)
        if japanese_voices: embed.add_field(name="**Japanese Voices**", value="\n".join(f"- {v}" for v in japanese_voices), inline=False)

        await interaction.followup.send(embed=embed)



async def setup(bot):
    await bot.add_cog(Voices(bot))