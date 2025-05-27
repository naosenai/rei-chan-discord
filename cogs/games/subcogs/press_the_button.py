import discord
from discord.ext import commands
from discord import app_commands

from .components.press_the_button_logic import PressTheButtonLogic

class PressTheButtonView(discord.ui.View):
    def __init__(self, question: PressTheButtonLogic):
        super().__init__()
        self.question = question

    async def button_logic(self, interaction, pressed: bool):
        self.question.press_button(pressed)
        description = (
            f"{self.question.benefit} \n**BUT**\n {self.question.drawback}\n"
            f"\n- **{self.question.percent_yes}** people{' also ' if pressed else ' '}pressed the button."
            f"\n- **{self.question.percent_no}** people{' 'if pressed else ' also '}did not press the button."
            )
        color = discord.Color.green() if pressed else discord.Color.red()
        embed = discord.Embed(
            title=f"You {'pressed' if pressed else 'did not press'} the button!",
            description=description,
            color=color,
            url=self.question.result_url
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Press the Button", style=discord.ButtonStyle.success)
    async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.button_logic(interaction, True)

    @discord.ui.button(label="I Will Not", style=discord.ButtonStyle.danger)
    async def dont_press(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.button_logic(interaction, False)

class PressTheButton(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def message_logic(self, interaction: discord.Interaction):
        user = interaction.user
        question = PressTheButtonLogic()
        
        embed = discord.Embed(
            title=f"Would you press the button?",
            description=f"{question.benefit} \n**BUT**\n {question.drawback}",
            color=discord.Color.orange(),
            url=question.question_url
        )
        embed.set_footer(text=f"Request by {user.display_name}", icon_url=user.avatar.url)

        view = PressTheButtonView(question)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.user_install
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="pressthebutton", description="Asks a random 'Would you press the button?' question.")
    async def truth(self, interaction: discord.Interaction):
        await self.message_logic(interaction)
    
async def setup(bot):
    await bot.add_cog(PressTheButton(bot))