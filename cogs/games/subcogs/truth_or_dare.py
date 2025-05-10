import discord
from discord.ext import commands
from discord import app_commands

from .components.truth_or_dare_questions import retrieve_question, get_keys

class TruthOrDare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def message_logic(self, interaction: discord.Interaction, qtype, category):
        user = interaction.user
        question = retrieve_question(qtype, category)
        
        embed = discord.Embed(
            title=question[0],
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Request by {user.display_name} | Question Type: {qtype} ({question[1]})", icon_url=user.avatar.url)

        view = discord.ui.View()
        view.add_item(self.ToDButton(self, interaction, "TRUTH", category, discord.ButtonStyle.success))
        view.add_item(self.ToDButton(self, interaction, "DARE", category, discord.ButtonStyle.danger))
        view.add_item(self.ToDButton(self, interaction, "RANDOM", category, discord.ButtonStyle.primary))
        await interaction.response.send_message(embed=embed, view=view)

    class ToDButton(discord.ui.Button):
        def __init__(self, cog: "TruthOrDare", msg, qtype, category, style):
            super().__init__(label=qtype.title(), style=style)
            self.cog = cog
            self.msg = msg
            self.qtype = qtype
            self.category = category

        async def callback(self, interaction: discord.Interaction):
            self.view.clear_items()
            await self.msg.edit_original_response(view=None)
            await self.cog.message_logic(interaction, self.qtype, self.category)
            self.view.stop()

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="truth", description="Sends a random truth question.")
    @app_commands.describe(type="The type of truth question to ask.")
    @app_commands.choices(type=[app_commands.Choice(name=key, value=key) for key in get_keys('TRUTH')])
    async def truth(self, interaction: discord.Interaction, type: str = "RANDOM"):
        await self.message_logic(interaction, "TRUTH", type)
    
    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="dare", description="Sends a random dare question.")
    @app_commands.describe(type="The type of dare to give.")
    @app_commands.choices(type=[app_commands.Choice(name=key, value=key) for key in get_keys('DARE')])
    async def dare(self, interaction: discord.Interaction, type: str = "RANDOM"):
        await self.message_logic(interaction, "DARE", type)

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="random", description="Sends a random Truth or Dare question.")
    async def random(self, interaction: discord.Interaction):
        await self.message_logic(interaction, None, None)

async def setup(bot):
    await bot.add_cog(TruthOrDare(bot))