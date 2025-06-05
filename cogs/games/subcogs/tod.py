import discord
from discord.ext import commands
from discord import app_commands

import csv
import random

CSV_PATH = 'cogs/games/subcogs/components/tod_questions.csv'

def get_categories(qtype):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return sorted(set(row['category'] for row in reader if row['type'].lower() == qtype.lower()))

def get_question(qtype=None, category="RANDOM"):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        questions = [
            row for row in reader
            if (qtype is None or row['type'].lower() == qtype.lower()) and
               (category.upper() == "RANDOM" or row['category'] == category)
        ]
    if not questions:
        return ["No question found.", "Unknown"]
    q = random.choice(questions)
    return [q['prompt'], q['category']]

class TruthOrDare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def message_logic(self, interaction: discord.Interaction, qtype, category):
        user = interaction.user
        question = get_question(qtype, category)

        embed = discord.Embed(
            title=question[0],
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Request by {user.display_name} | Question Type: {qtype or 'RANDOM'} ({question[1]})", icon_url=user.avatar.url)

        view = discord.ui.View()
        view.add_item(self.ToDButton(self, interaction, "TRUTH", category, discord.ButtonStyle.success))
        view.add_item(self.ToDButton(self, interaction, "DARE", category, discord.ButtonStyle.danger))
        view.add_item(self.ToDButton(self, interaction, "RANDOM", category, discord.ButtonStyle.primary))
        await interaction.response.send_message(embed=embed, view=view)

    class ToDButton(discord.ui.Button):
        def __init__(self, cog, msg, qtype, category, style):
            super().__init__(label=qtype.title(), style=style)
            self.cog = cog
            self.msg = msg
            self.qtype = qtype
            self.category = category

        async def callback(self, interaction: discord.Interaction):
            self.view.clear_items()
            await self.msg.edit_original_response(view=None)
            await self.cog.message_logic(interaction, self.qtype.lower() if self.qtype != "RANDOM" else None, self.category)
            self.view.stop()

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="truth", description="Sends a random truth question.")
    @app_commands.choices(type=[app_commands.Choice(name=cat, value=cat) for cat in get_categories("truth")] + [app_commands.Choice(name="RANDOM", value="RANDOM")])
    async def truth(self, interaction: discord.Interaction, type: str = "RANDOM"):
        await self.message_logic(interaction, "truth", type)

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="dare", description="Sends a random dare question.")
    @app_commands.choices(type=[app_commands.Choice(name=cat, value=cat) for cat in get_categories("dare")] + [app_commands.Choice(name="RANDOM", value="RANDOM")])
    async def dare(self, interaction: discord.Interaction, type: str = "RANDOM"):
        await self.message_logic(interaction, "dare", type)

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="random", description="Sends a random Truth or Dare question.")
    async def random(self, interaction: discord.Interaction):
        await self.message_logic(interaction, None, "RANDOM")

async def setup(bot):
    await bot.add_cog(TruthOrDare(bot))