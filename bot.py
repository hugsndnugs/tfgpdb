import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DEFAULT_PREFIX = os.getenv('DEFAULT_PREFIX', '!')

# Set up bot with all intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents)

# Load cogs
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    await bot.change_presence(activity=discord.Game(name="Use / commands"))

@bot.event
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.errors.CommandNotFound):
        await interaction.response.send_message("Command not found. Use /help to see available commands.", ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, app_commands.errors.CheckFailure):
        await interaction.response.send_message("You don't meet the requirements to use this command.", ephemeral=True)
    elif isinstance(error, discord.Forbidden):
        await interaction.response.send_message("I don't have the required permissions to perform this action.", ephemeral=True)
    else:
        # Log the full error
        logging.error(f"Command error: {error}", exc_info=True)
        await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)

@bot.event
async def on_error(event, *args, **kwargs):
    logging.error(f"Event error in {event}", exc_info=True)

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 