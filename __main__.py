import os
import discord
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')                    

intents = discord.Intents.default()
#intents.members = True
#intents.presences = True
#intents.message_content = True

bot = commands.Bot(command_prefix='a?', intents=intents)

cogs = ['cogs.music']

@bot.event
async def on_ready():
    try:
        for cog in cogs:
            current_cog = cog
            await bot.load_extension(cog)
    except Exception as e:
        print(f'Error loading extention at \"{current_cog}\": {e}')
    try:
        await bot.tree.sync()
        print(f'Commands synced successfully!')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Unexpected error occurred: {event}, {args}, {kwargs}")

bot.run(TOKEN)
