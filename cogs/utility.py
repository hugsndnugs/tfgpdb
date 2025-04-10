import discord
from discord import app_commands
from discord.ext import commands
import datetime
import pytz
import aiohttp
import os
from dotenv import load_dotenv

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()  # Load environment variables
        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY', 'YOUR_API_KEY')

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f'Pong! Latency: {latency}ms')

    @app_commands.command(name="serverinfo", description="Display information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(
            title=f"Server Information - {guild.name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Server ID", value=guild.id, inline=False)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%B %d, %Y"), inline=False)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=False)
        embed.add_field(name="Members", value=guild.member_count, inline=False)
        embed.add_field(name="Roles", value=len(guild.roles), inline=False)
        embed.add_field(name="Channels", value=len(guild.channels), inline=False)
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Display information about a user")
    @app_commands.describe(member="The user to get information about (leave empty for yourself)")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        
        embed = discord.Embed(
            title=f"User Information - {member.name}",
            color=member.color
        )
        
        embed.add_field(name="User ID", value=member.id, inline=False)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%B %d, %Y"), inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%B %d, %Y"), inline=False)
        
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            embed.add_field(name="Roles", value=", ".join(roles), inline=False)
        else:
            embed.add_field(name="Roles", value="None", inline=False)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="time", description="Get the current time in a specific timezone")
    @app_commands.describe(timezone="The timezone to show (e.g., America/New_York, Europe/London)")
    async def time(self, interaction: discord.Interaction, timezone: str = None):
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                current_time = datetime.datetime.now(tz)
                embed = discord.Embed(
                    title=f"Time in {timezone}",
                    description=current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
            except pytz.exceptions.UnknownTimeZoneError:
                await interaction.response.send_message(
                    "Invalid timezone! Please use a valid timezone (e.g., 'America/New_York')", 
                    ephemeral=True
                )
        else:
            current_time = datetime.datetime.now()
            embed = discord.Embed(
                title="Current Time (UTC)",
                description=current_time.strftime('%Y-%m-%d %H:%M:%S'),
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="weather", description="Get weather information for a city")
    @app_commands.describe(city="The name of the city to get weather for")
    async def weather(self, interaction: discord.Interaction, city: str):
        await interaction.response.defer()  # This might take a moment
        
        # Use the API key from environment variables
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.weather_api_key}&units=metric') as response:
                if response.status == 200:
                    data = await response.json()
                    temp = data['main']['temp']
                    desc = data['weather'][0]['description']
                    humidity = data['main']['humidity']
                    wind_speed = data['wind']['speed']
                    
                    embed = discord.Embed(
                        title=f"Weather in {city}",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Temperature", value=f"{temp}°C", inline=True)
                    embed.add_field(name="Description", value=desc.capitalize(), inline=True)
                    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                    embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Couldn't fetch weather information. Please try again later!")

async def setup(bot):
    await bot.add_cog(Utility(bot)) 