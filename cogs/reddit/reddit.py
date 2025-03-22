from discord.ext import commands

from .subcogs import RSSFeed



class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    cog = Reddit(bot)
    await bot.add_cog(cog)
    await bot.add_cog(RSSFeed(bot))
