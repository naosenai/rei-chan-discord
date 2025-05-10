import aiohttp
import io
from PIL import Image

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View

from .components import vocaloid_scraper as vs
    


class LyricsSession:
    def __init__(self, interaction: discord.Interaction, query):
        self.interaction = interaction
        self.query = "https://vocaloidlyrics.fandom.com/wiki/" + query
        self.user = interaction.user
        self.msg = None

        self.data = None
        self.color = None
        self.external_links = None
        self.video = None
        self.video_msg = None
        self.lyrics_page = None

        #This will be revised for localization later
        self.embed_footer = f"Requested by {self.user.display_name} • Powered by vocaloidlyrics.fandom.com"

    async def initialize(self):
        embed = discord.Embed(
            title=f"Fetching results for \"{self.query}\"...",
            color=discord.Color.orange())
        
        self.msg = await self.interaction.followup.send(embed=embed)
        self.data = vs.Song(self.query)
        self.color = await self.get_average_color(self.data.image)
        self.external_links = "\n".join([f"• [{link['title']}]({link['href']})" for link in self.data.links])
        self.video = next((link['href'] for link in self.data.links if link['title'] == "YouTube Broadcast"), None)
        self.lyrics_page = ["Original", 0]

    async def get_average_color(self, image_url: str) -> int:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                image_data = await response.read()
    
        image = Image.open(io.BytesIO(image_data))
        image = image.resize((100, 100)) # Resize to reduce load
        image = image.convert("RGB")

        pixels = list(image.getdata())
        avg_color = tuple(map(lambda x: sum(x) // len(x), zip(*pixels)))

        avg_color_hex = (avg_color[0] << 16) + (avg_color[1] << 8) + avg_color[2]
        return avg_color_hex

class LyricsView(View):
    def __init__(self, session: LyricsSession):
        super().__init__(timeout=600)
        self.session = session
        self.disable_buttons()

    def disable_buttons(self):
        disabled_list = [
            self.session.lyrics_page[1] == 0,
            self.session.lyrics_page[1] == 1 or len(self.session.data.lyrics) < 2 or self.session.data.lyrics[1] == "",
            self.session.lyrics_page[1] == 2 or len(self.session.data.lyrics) < 3 or self.session.data.lyrics[2] == "",
            not self.session.video
            ]
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id in {"0", "1", "2", "3"}:
                    item.disabled = disabled_list[int(item.custom_id)]

    def stop(self):
        super().stop()
        self.clear_items()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.session.user:
            await interaction.response.send_message("Only the command sender can use these buttons!", ephemeral=True)
            return False
        if not interaction.response.is_done():
            await interaction.response.defer()
        return True
    
    async def lyrics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.interaction_check(interaction):
            return
        self.stop()
        self.session.lyrics_page = [button.label, int(button.custom_id)]
        await lyrics_embed(self.session)
        await lyrics_view(self.session)

    @discord.ui.button(label="Original", row=1, custom_id='0', style=discord.ButtonStyle.primary)
    async def original_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lyrics_button(interaction, button)

    @discord.ui.button(label="Romanized", row=1, custom_id='1', style=discord.ButtonStyle.primary)
    async def romanized_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lyrics_button(interaction, button)

    @discord.ui.button(label="Translated", row=1, custom_id='2', style=discord.ButtonStyle.primary)
    async def translated_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lyrics_button(interaction, button)

    @discord.ui.button(label="YouTube Popout", row=2, custom_id='3', style=discord.ButtonStyle.secondary)
    async def youtube_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.interaction_check(interaction):
            return
        if not self.session.video_msg:
            self.session.video_msg = await interaction.followup.send(content=f"{self.session.video}")
        else:
            await self.session.video_msg.delete()
            self.session.video_msg = None
        await lyrics_embed(self.session)

    @discord.ui.button(label="✖", row=2, style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.interaction_check(interaction):
            return
        if self.session.video_msg:
            await self.session.video_msg.delete()
        await self.session.msg.delete()

async def lyrics_embed(session):
    embed = discord.Embed(
        url=session.data.query,
        title=f"{session.lyrics_page[0]} lyrics for {session.data.title}",
        color=discord.Color(session.color),
        description=session.data.lyrics[session.lyrics_page[1]],
    )

    embed.add_field(name=f"\u200B", value="\u200B") # Padding between lyrics & extras
    embed.add_field(name=f"═ External Links ═", value=session.external_links, inline=False)

    if not session.video_msg:
        embed.set_image(url=session.data.image)

    embed.set_footer(text=session.embed_footer, icon_url=session.user.avatar.url)

    await session.msg.edit(embed=embed)

async def lyrics_view(session):
    view = LyricsView(session)
    await session.msg.edit(view=view)

async def initialize_lyrics(session):
    if not session.data.lyrics:
        embed = discord.Embed(
            title=f"No lyrics discovered for {session.data.title}",
            color=discord.Color.orange()
        )
        await session.msg.edit(embed=embed)
        return
    await lyrics_embed(session)
    await lyrics_view(session)

class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.link = "https://vocaloidlyrics.fandom.com/wiki/"
    
    async def lyrics_fallback(self, interaction:discord.Interaction, search: str) -> str:
        song = vs.Song(self.link + search)
        if not song.error_message:
            await interaction.response.defer()
            return search
        
        song = vs.Song(search)
        embed = discord.Embed(
            title="I couldn't find the page you inputted.",
            description="This is likely because you didn't select an option for your query. " +
            "For more results, try using the autocomplete options." +
            "\nI will attempt to redirect you to the first result for your query.",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return song.links[0]["href"].replace(self.link, "")

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="lyrics", description="Enter a name of a vocaloid song to search Fandom for its lyrics!")
    @app_commands.describe(search="Enter a song name and options to select from will appear!")
    async def lyrics(self, interaction: discord.Interaction, search: str):
        if interaction.response.is_done():
            await interaction.response.defer()
        search = await self.lyrics_fallback(interaction, search)
        session = LyricsSession(interaction, search)
        await session.initialize()
        await initialize_lyrics(session)
        
    @lyrics.autocomplete('search')
    async def lyrics_autocomplete(self, interaction: discord.Interaction, current: str):
        await interaction.response.defer()
        if not current:
            return [app_commands.Choice(name="Start typing to see results!", value=" ") ]

        song_data = vs.Song(current)
        songs = [
            (song["title"], song["href"].replace(self.link, ""))
            for song in song_data.links
            if len(song["title"]) <= 100 and len(song["href"]) <= 100
        ]

        return [
            app_commands.Choice(name=song[0], value=song[1]) 
            for song in songs
        ]



async def setup(bot):
    await bot.add_cog(Lyrics(bot))