import json
import time
import os
import re

import discord
from discord.ext import commands, tasks
import feedparser

import requests
from bs4 import BeautifulSoup



USER_AGENT = os.getenv('USER_AGENT')
FEED_CHANNELS = {
    os.getenv('QUEUE_RSS_URL'): {
        'channel': os.getenv('QUEUE_RSS_CHANNEL'), 
        'type': 'queue'
    },
    os.getenv('LOG_RSS_URL'): {
        'channel': os.getenv('LOG_RSS_CHANNEL'),
        'type': 'log'
    } ,
    os.getenv('REPORT_RSS_URL'): {
        'channel': os.getenv('REPORT_RSS_CHANNEL'),
        'type': 'report'
    }
}

class RSSFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.newest_timestamp = 0
        self.data_folder = None
        self.time_files = {}
        self.guild = None

    def cog_unload(self):
        self.rss_feed_task.cancel()

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
    
    def formatted_description(self, entry):
        html_content = entry.get('content', [{}])[0].get('value')
        soup = BeautifulSoup(html_content, 'html.parser')

        for submitted_tag in soup.find_all(string=re.compile(r'\bsubmitted by\b')):
            parent_tag = submitted_tag.find_parent()
            if parent_tag:
                for link_tag in parent_tag.find_all('a', string=re.compile(r'/u/')):
                    link_tag.decompose()
                submitted_tag.extract()

        comments_link = soup.find('a', string='[comments]')
        if comments_link:
            comments_link.decompose()

        for a_tag in soup.find_all('a'):
            link_text = a_tag.get_text()
            link_url = a_tag.get('href')
            a_tag.replace_with(f'[{link_text}]({link_url})')

        return f"{soup.get_text(separator=' ', strip=True)}"
        
    async def queue_message(self, entry, channel):
        embed = discord.Embed(title=f"{entry.get('title')}",
                      url=f"{entry.get('link')}",
                      description=self.formatted_description(entry),
                      colour=0xf91565)
        embed.set_author(name="Mod Queue for r/sfwteto",
                        icon_url="https://styles.redditmedia.com/t5_daczgy/styles/communityIcon_6jbxb9pgt8be1.png")
        embed.set_image(url=entry.get('image__url'))
        embed.set_footer(text=f"{entry.author} submitted for review at {entry.date}")

        view = discord.ui.View()
        queue_button = discord.ui.Button(style=discord.ButtonStyle.link, label="📋Queue", url="https://www.reddit.com/mod/sfwteto/queue/")
        author_button = discord.ui.Button(style=discord.ButtonStyle.link, label="👤Author", url=f"{entry.get('authors', [{}])[0].get('href')}")
        post_button = discord.ui.Button(style=discord.ButtonStyle.link, label="🔗Post", url=f"{entry.get('link')}")
        view.add_item(queue_button)
        view.add_item(author_button)
        view.add_item(post_button)

        role = self.guild.get_role(int(os.getenv('QUEUE_RSS_PING')))
        mention = role.mention
        await channel.send(f"{mention}", embed=embed, view=view)
    
    async def log_message(self, entry, channel):
        embed = discord.Embed(title=entry.get('title'),
                      url=entry.get('link'),
                      colour=0xf91565)
        embed.set_author(name="Mod Log for r/sfwteto",
                        icon_url="https://styles.redditmedia.com/t5_daczgy/styles/communityIcon_6jbxb9pgt8be1.png")
        embed.set_footer(text=f"{entry.get('author')} executed this action at {entry.get('date')}")

        view = discord.ui.View()
        #queue_button = discord.ui.Button(style=discord.ButtonStyle.link, label="📋Mod Action", url=entry.get('id'))
        profile_button = discord.ui.Button(style=discord.ButtonStyle.link, label="👤Mod Profile", url=entry.get('href'))
        link_button = discord.ui.Button(style=discord.ButtonStyle.link, label="🔗Affected Post", url=entry.get('link'))
        #view.add_item(queue_button)
        view.add_item(profile_button)
        view.add_item(link_button)
        
        role = self.guild.get_role(int(os.getenv('LOG_RSS_PING')))
        mention = role.mention
        await channel.send(f"{mention}", embed=embed, view=view)

    async def report_message(self, entry, channel):
        await self.queue_message(entry, channel) # For now, just send the same message as a queue message

    @tasks.loop(minutes=3)
    async def rss_feed_task(self):
        self.guild = await self.bot.fetch_guild(int(os.getenv('GUILD_ID')))
        try:
            for feed_url, feed_info in FEED_CHANNELS.items():
                headers = {
                    'User-Agent': USER_AGENT
                }
                response = requests.get(feed_url, headers=headers)
                if response.status_code != 200:
                    print(f"Error fetching feed: {response.status_code}")
                    continue
                else:
                    rss_entries = feedparser.parse(response.text).entries
                    rss_entries.reverse()

                type = feed_info['type']
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
                self.newest_timestamp = 0

        except Exception as e:
            print(f"Error fetching Reddit RSS feed: {e}")

async def setup(bot):
    await bot.add_cog(RSSFeed(bot))