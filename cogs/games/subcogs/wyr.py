import discord
from discord.ext import commands
from discord import app_commands

import csv
import random

class WouldYouRatherView(discord.ui.View):
    def __init__(self, question: dict):
        super().__init__()
        self.question = question

    async def button_logic(self, interaction, option: bool):
        description = (
            f"{self.question['option_a']} \n**OR**\n {self.question['option_b']}\n"
            f"\n- **{self.question['votes_a']}** people{' also ' if option else ' '}voted option 1."
            f"\n- **{self.question['votes_b']}** people{' 'if option else ' also '}voted option 2."
            )
        color = discord.Color.green() if option else discord.Color.red()
        embed = discord.Embed(
            title=f"You voted for option {'1' if option else '2'}!",
            description=description,
            color=color
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Option 1", style=discord.ButtonStyle.success)
    async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.button_logic(interaction, True)

    @discord.ui.button(label="Option 2", style=discord.ButtonStyle.danger)
    async def dont_press(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.button_logic(interaction, False)

class WouldYouRather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def message_logic(self, interaction: discord.Interaction):
        user = interaction.user
        with open('cogs/games/subcogs/components/wyr_questions.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            question = random.choice(rows)
        
        embed = discord.Embed(
            title=f"What would you rather??",
            description=f"{question['option_a']} \n**OR**\n {question['option_b']}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Request by {user.display_name}", icon_url=user.avatar.url)

        view = WouldYouRatherView(question)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="wouldyourather", description="Asks a random 'Would you rather?' question.")
    async def truth(self, interaction: discord.Interaction):
        await self.message_logic(interaction)
    
async def setup(bot):
    await bot.add_cog(WouldYouRather(bot))