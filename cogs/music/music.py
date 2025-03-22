from discord.ext import commands

from .subcogs import Lyrics



class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    cog = Music(bot)
    await bot.add_cog(cog)
    await bot.add_cog(Lyrics(bot))
