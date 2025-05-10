from os import getenv
import discord
from discord.ext import commands
from dotenv import load_dotenv
import time



start_time = time.time()

load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')  

cogs = [
    'cogs.audio.audio',
    'cogs.reddit.reddit',
    'cogs.games.games'
]

class Rei(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_first_boot = True

    async def setup_hook(self):
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"{cog} loaded successfully!")
            except Exception as e:
                print(f"Failed to load cog {cog}: {e}")
        elapsed_time = time.time() - start_time
        print(f"Preloading finished in {elapsed_time:.2f} seconds, {self.user} is waking up!")

    async def on_ready(self):
        if self.is_first_boot:
            await self.sync_commands()
            await self.start_rss_feed_task()
            self.is_first_boot = False

    async def on_error(self, event, *args, **kwargs):
        print(f"Unexpected error occurred: {event}, {args}, {kwargs}")

    async def sync_commands(self):
        try:
            await self.tree.sync()
            elapsed_time = time.time() - start_time
            print(f"Commands synced successfully after {elapsed_time:.2f} seconds!")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def start_rss_feed_task(self):
        try:
            feed = self.get_cog('RSSFeed')
            await feed.rss_feed_task.start()
        except Exception as e:
            print(f"Error starting RSS feed task: {e}")

intents = discord.Intents.default()
intents.message_content = True
#intents.members = True
#intents.presences = True

bot = Rei(command_prefix='a?', intents=intents)

bot.run(TOKEN)
