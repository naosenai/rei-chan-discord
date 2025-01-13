import json
import time
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks
import feedparser

#import requests
#from requests.auth import HTTPBasicAuth



#CLIENT_ID = os.getenv('CLIENT_ID')
#CLIENT_SECRET = os.getenv('CLIENT_SECRET')
#USER_AGENT = os.getenv('USER_AGENT')
#USERNAME = os.getenv('USERNAME')
#PASSWORD = os.getenv('PASSWORD')

FEED_CHANNELS = {
    os.getenv('QUEUE_RSS_URL'): {
        'channel': os.getenv('QUEUE_RSS_CHANNEL'), 
        'type': 'queue'
    },
    os.getenv('LOG_RSS_URL'): {
        'channel': os.getenv('LOG_RSS_CHANNEL'),
        'type': 'log'
    }  
}

class RedditRSSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.newest_timestamp = None
        self.data_folder = None
        self.time_files = {}
        #self.access_token = None
        #self.refresh_token = None
        #self.token_expires_at = None

    def cog_unload(self):
        self.rss_feed_task.cancel()

    # Found out reddit provides unlocked RSS feeds :facepalm:
    # Some of this code may still be useful for scraping other information though
    '''
    def request_token(self, data: dict):
        auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
        headers = {'User-Agent': USER_AGENT}
        data = data
        response = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
        print(response.json())

        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            self.token_expires_at = time.time() + tokens['expires_in']
            return self.access_token
        else:
            raise Exception(f"Failed to obtain token: {response.status_code}")

    def get_access_token(self):
        data = {
            'grant_type': 'password',
            'username': USERNAME,
            'password': PASSWORD
        }
        return self.request_token(data)


    def refresh_access_token(self):
        if not self.refresh_token:
            raise Exception("No refresh token available.")
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        return self.request_token(data)


    def fetch_reddit_rss_feed(self, feed_url):
        if self.token_expires_at is None or time.time() > self.token_expires_at:
            self.get_access_token()
        elif time.time() > self.token_expires_at - 300:  # Refresh ~5 minutes before expiration
            self.refresh_access_token()

        headers = {
            'Authorization': f'bearer {self.access_token}',
            'User-Agent': USER_AGENT
        }

        response = requests.get(feed_url, headers=headers)

        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            return feed.entries
        else:
            raise Exception(f"Failed to fetch Reddit RSS feed: {response.status_code}")
    '''

    def set_dir(self):
        self.data_folder = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

    def set_path(self, type):
        if not self.data_folder:
            self.set_dir()
        if not self.time_files.get(type):
            self.time_files.update({type: os.path.join(self.data_folder, f"timestamp_{type}.json")})
        return self.time_files[type]

    def load_last_post_time(self, type):
        path = self.set_path(type)
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get('post_timestamp', 0)  
        except FileNotFoundError:
            self.save_last_post_time(0, type)
            return 0  

    def save_last_post_time(self, last_post_time, type):
        path = self.set_path(type)
        with open(path, "w") as f:
            json.dump({"post_timestamp": last_post_time}, f)

    def is_post_too_old(self, post_time, type):
        prev_time = self.load_last_post_time(type)
        return post_time <= prev_time
        
    async def queue_message(self, entry, channel):
        embed = discord.Embed(title=f"{entry.title}",
                      url=f"{entry.link}",
                      description=f"TEMPORARY\n```{entry}```",
                      colour=0xf91565)
        embed.set_author(name="Mod Queue for r/sfwteto",
                        icon_url="https://styles.redditmedia.com/t5_daczgy/styles/communityIcon_6jbxb9pgt8be1.png")
        embed.set_image(url=f"{entry.image__url}")
        embed.set_footer(text=f"{entry.author} submitted for review at {entry.date}")

        view = discord.ui.View()
        queue_button = discord.ui.Button(style=discord.ButtonStyle.link, label="📋Queue", url="https://www.reddit.com/mod/sfwteto/queue/")
        author_button = discord.ui.Button(style=discord.ButtonStyle.link, label="👤Author", url=f"{entry.author__url}")
        post_button = discord.ui.Button(style=discord.ButtonStyle.link, label="🔗Post", url=f"{entry.link}")
        view.add_item(queue_button)
        view.add_item(author_button)
        view.add_item(post_button)
        
        await channel.send(embed=embed, view=view)
    
    async def log_message(self, entry, channel):
        embed = discord.Embed(title=f"{entry.title}",
                      url=f"{entry.link}",
                      colour=0xf91565)
        embed.set_author(name="Mod Log for r/sfwteto",
                        icon_url="https://styles.redditmedia.com/t5_daczgy/styles/communityIcon_6jbxb9pgt8be1.png")
        embed.set_footer(text=f"{entry.author} executed this action at {entry.date}")

        view = discord.ui.View()
        queue_button = discord.ui.Button(style=discord.ButtonStyle.link, label="📋Mod Action", url=f"{entry.id}")
        profile_button = discord.ui.Button(style=discord.ButtonStyle.link, label="👤Mod Profile", url=f"{entry.href}")
        link_button = discord.ui.Button(style=discord.ButtonStyle.link, label="🔗Affected Post", url=f"{entry.link}")
        view.add_item(queue_button)
        view.add_item(profile_button)
        view.add_item(link_button)
        
        await channel.send(embed=embed, view=view)

    @tasks.loop(minutes=2)
    async def rss_feed_task(self):
        try:
            for feed_url, feed_info in FEED_CHANNELS.items():
                rss_entries = feedparser.parse(feed_url).entries
                rss_entries.reverse()

                if not rss_entries:
                    continue

                type = feed_info['type']
                channel = self.bot.get_channel(feed_info['channel'])
                if not channel:
                    channel = await self.bot.fetch_channel(feed_info['channel'])

                message_function = getattr(self, f'{type}_message', None)
                if not message_function:
                    print(f"Error: No function found for {type} messages")
                    continue
                
                for entry in rss_entries:
                    updated_time = time.mktime(entry['updated_parsed'])  
                    if not self.newest_timestamp or updated_time > self.newest_timestamp:
                        self.newest_timestamp = updated_time

                    if self.is_post_too_old(updated_time, type):
                        continue

                    await message_function(entry, channel)
                    time.sleep(1)

                self.save_last_post_time(self.newest_timestamp, type)
                self.newest_timestamp = None

        except Exception as e:
            print(f"Error fetching Reddit RSS feed: {e}")

async def setup(bot):
    await bot.add_cog(RedditRSSCog(bot))