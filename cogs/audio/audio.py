from discord.ext import commands

from .subcogs import Lyrics
from .subcogs import TTS
from .subcogs import Voices



class Audio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    cog = Audio(bot)
    await bot.add_cog(cog)
    await bot.add_cog(Lyrics(bot))
    await bot.add_cog(TTS(bot))
    await bot.add_cog(Voices(bot))
