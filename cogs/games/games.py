from discord.ext import commands

from .subcogs import TruthOrDare



class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    cog = Games(bot)
    await bot.add_cog(cog)
    await bot.add_cog(TruthOrDare(bot))
