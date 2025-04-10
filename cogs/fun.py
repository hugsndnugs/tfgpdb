import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
import json

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a dice in NdN format (e.g., 2d6)")
    @app_commands.describe(dice="Dice in NdN format (e.g., 2d6 for two six-sided dice)")
    async def roll(self, interaction: discord.Interaction, dice: str):
        try:
            rolls, limit = map(int, dice.split('d'))
            if rolls > 20:
                await interaction.response.send_message('Cannot roll more than 20 dice at once.', ephemeral=True)
                return
            if limit > 100:
                await interaction.response.send_message('Cannot use dice with more than 100 sides.', ephemeral=True)
                return
                
            results = [random.randint(1, limit) for _ in range(rolls)]
            await interaction.response.send_message(f'Result: {", ".join(map(str, results))} (Total: {sum(results)})')
        except Exception:
            await interaction.response.send_message('Format has to be in NdN! For example, 2d6 for two six-sided dice.', ephemeral=True)

    @app_commands.command(name="choose", description="Choose between multiple options")
    @app_commands.describe(options="Comma-separated list of options to choose from")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [option.strip() for option in options.split(',')]
        if len(choices) < 2:
            await interaction.response.send_message('Please provide at least two options separated by commas.', ephemeral=True)
            return
            
        await interaction.response.send_message(f'I choose: {random.choice(choices)}')

    @app_commands.command(name="rps", description="Play rock paper scissors with the bot")
    @app_commands.describe(choice="Your choice: rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name='Rock', value='rock'),
        app_commands.Choice(name='Paper', value='paper'),
        app_commands.Choice(name='Scissors', value='scissors')
    ])
    async def rps(self, interaction: discord.Interaction, choice: str):
        choices = ['rock', 'paper', 'scissors']
        bot_choice = random.choice(choices)
        
        if choice.lower() == bot_choice:
            await interaction.response.send_message(f"It's a tie! We both chose {bot_choice}!")
        elif (choice.lower() == 'rock' and bot_choice == 'scissors') or \
             (choice.lower() == 'paper' and bot_choice == 'rock') or \
             (choice.lower() == 'scissors' and bot_choice == 'paper'):
            await interaction.response.send_message(f"You win! I chose {bot_choice}!")
        else:
            await interaction.response.send_message(f"I win! I chose {bot_choice}!")

    @app_commands.command(name="meme", description="Get a random meme from Reddit")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()  # This might take a moment
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meme-api.com/gimme') as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(title=data['title'], color=discord.Color.blue())
                    embed.set_image(url=data['url'])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Couldn't fetch a meme right now. Try again later!")

    @app_commands.command(name="quote", description="Get a random inspirational quote")
    async def quote(self, interaction: discord.Interaction):
        await interaction.response.defer()  # This might take a moment
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://zenquotes.io/api/random') as response:
                if response.status == 200:
                    data = await response.json()
                    quote = data[0]['q']
                    author = data[0]['a']
                    embed = discord.Embed(description=f'"{quote}"', color=discord.Color.blue())
                    embed.set_author(name=author)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Couldn't fetch a quote right now. Try again later!")

async def setup(bot):
    await bot.add_cog(Fun(bot)) 