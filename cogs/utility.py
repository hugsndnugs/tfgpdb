import discord
from discord import app_commands
from discord.ext import commands
import datetime
import pytz
import aiohttp
import os
from dotenv import load_dotenv
from typing import Optional

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

    @app_commands.command(name="help", description="Shows a list of available commands and features")
    async def help(self, interaction: discord.Interaction, category: Optional[str] = None):
        if category is None:
            # Create a main help embed with feature categories
            embed = discord.Embed(
                title="Bot Help",
                description="Here are all the available feature categories. Use `/help <category>` to see specific commands.",
                color=discord.Color.blue()
            )
            
            # Add fields for each category
            embed.add_field(name="🛡️ Moderation", value="Server moderation commands", inline=True)
            embed.add_field(name="🎮 Fun", value="Fun and entertaining commands", inline=True)
            embed.add_field(name="🔧 Utility", value="Useful utility commands", inline=True)
            embed.add_field(name="📈 Leveling", value="XP and leveling system", inline=True)
            embed.add_field(name="👋 Welcome", value="Welcome and goodbye messages", inline=True)
            embed.add_field(name="🔒 Auto-Moderation", value="Automatic message moderation", inline=True)
            embed.add_field(name="📊 Polls", value="Create and manage polls", inline=True)
            embed.add_field(name="🏷️ Reaction Roles", value="Self-assignable roles", inline=True)
            embed.add_field(name="⚙️ Custom Commands", value="Server-specific commands", inline=True)
            embed.add_field(name="🎁 Giveaways", value="Host giveaways for your members", inline=True)
            embed.add_field(name="📅 Scheduled Messages", value="Schedule announcements", inline=True)
            embed.add_field(name="🎵 Music", value="Play music in voice channels", inline=True)
            embed.add_field(name="🎫 Tickets", value="User support ticket system", inline=True)
            
            embed.set_footer(text="Use /help <category> for more details on a specific category")
        else:
            # Convert to lowercase and remove spaces/dashes
            category = category.lower().replace(" ", "").replace("-", "")
            
            if category in ["mod", "moderation"]:
                embed = discord.Embed(
                    title="🛡️ Moderation Commands",
                    description="Server moderation commands",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/kick", value="Kick a member from the server", inline=False)
                embed.add_field(name="/ban", value="Ban a member from the server", inline=False)
                embed.add_field(name="/unban", value="Unban a member from the server", inline=False)
                embed.add_field(name="/clear", value="Clear a specified number of messages", inline=False)
                embed.add_field(name="/mute", value="Mute a member", inline=False)
                embed.add_field(name="/unmute", value="Unmute a member", inline=False)
                
            elif category in ["fun"]:
                embed = discord.Embed(
                    title="🎮 Fun Commands",
                    description="Fun and entertaining commands",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/roll", value="Roll dice in NdN format (e.g., 2d6)", inline=False)
                embed.add_field(name="/choose", value="Choose between multiple options", inline=False)
                embed.add_field(name="/rps", value="Play rock paper scissors", inline=False)
                embed.add_field(name="/meme", value="Get a random meme", inline=False)
                embed.add_field(name="/quote", value="Get a random inspirational quote", inline=False)
                
            elif category in ["utility", "util"]:
                embed = discord.Embed(
                    title="🔧 Utility Commands",
                    description="Useful utility commands",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/ping", value="Check bot latency", inline=False)
                embed.add_field(name="/serverinfo", value="Display server information", inline=False)
                embed.add_field(name="/userinfo", value="Display user information", inline=False)
                embed.add_field(name="/time", value="Get current time", inline=False)
                embed.add_field(name="/weather", value="Get weather information", inline=False)
                
            elif category in ["level", "levels", "leveling", "xp"]:
                embed = discord.Embed(
                    title="📈 Leveling Commands",
                    description="XP and leveling system",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/rank", value="Check your or someone else's level and XP", inline=False)
                embed.add_field(name="/leaderboard", value="View the server's XP leaderboard", inline=False)
                
            elif category in ["welcome", "welcomesystem"]:
                embed = discord.Embed(
                    title="👋 Welcome System Commands",
                    description="Welcome and goodbye messages",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/setwelcomechannel", value="Set the channel for welcome messages", inline=False)
                embed.add_field(name="/setgoodbyechannel", value="Set the channel for goodbye messages", inline=False)
                embed.add_field(name="/setwelcomemessage", value="Customize welcome messages", inline=False)
                embed.add_field(name="/setgoodbyemessage", value="Customize goodbye messages", inline=False)
                embed.add_field(name="/togglewelcomedm", value="Toggle welcome DMs", inline=False)
                embed.add_field(name="/setwelcomedmmessage", value="Customize welcome DM messages", inline=False)
                
            elif category in ["automod", "automoderation"]:
                embed = discord.Embed(
                    title="🔒 Auto-Moderation Commands",
                    description="Automatic message moderation",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/automod", value="Toggle auto-moderation", inline=False)
                embed.add_field(name="/automodlog", value="Set logging channel", inline=False)
                embed.add_field(name="/addfilterword", value="Add words to filter", inline=False)
                embed.add_field(name="/removefilterword", value="Remove words from filter", inline=False)
                embed.add_field(name="/filterwords", value="List filtered words", inline=False)
                embed.add_field(name="/allowserver", value="Allow Discord invites from specific servers", inline=False)
                embed.add_field(name="/disallowserver", value="Disallow invites from servers", inline=False)
                
            elif category in ["poll", "polls"]:
                embed = discord.Embed(
                    title="📊 Poll Commands",
                    description="Create and manage polls",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/poll", value="Create a poll with multiple options", inline=False)
                embed.add_field(name="/quickpoll", value="Create a simple yes/no poll", inline=False)
                embed.add_field(name="/endpoll", value="End a poll early and display results", inline=False)
                
            elif category in ["reactionroles", "roles", "reaction"]:
                embed = discord.Embed(
                    title="🏷️ Reaction Roles Commands",
                    description="Self-assignable roles",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/reactionrole", value="Create a reaction role message", inline=False)
                embed.add_field(name="/addrole", value="Add a role to a reaction role message", inline=False)
                embed.add_field(name="/removerole", value="Remove a role from a reaction role message", inline=False)
                embed.add_field(name="/listroles", value="List all roles in a reaction role message", inline=False)
                
            elif category in ["customcommands", "custom", "commands"]:
                embed = discord.Embed(
                    title="⚙️ Custom Commands",
                    description="Server-specific commands",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/addcmd", value="Add a custom command", inline=False)
                embed.add_field(name="/editcmd", value="Edit an existing custom command", inline=False)
                embed.add_field(name="/removecmd", value="Remove a custom command", inline=False)
                embed.add_field(name="/listcmds", value="List all custom commands", inline=False)
                embed.add_field(name="/cmdinfo", value="View detailed information about a command", inline=False)
                
            elif category in ["giveaway", "giveaways"]:
                embed = discord.Embed(
                    title="🎁 Giveaway Commands",
                    description="Host giveaways for your members",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/giveaway", value="Start a new giveaway", inline=False)
                embed.add_field(name="/giveaway_end", value="End a giveaway early", inline=False)
                embed.add_field(name="/giveaway_reroll", value="Reroll winners for a giveaway", inline=False)
                embed.add_field(name="/giveaway_list", value="List all active giveaways", inline=False)
                
            elif category in ["schedule", "schedules", "scheduled", "announcement", "announcements"]:
                embed = discord.Embed(
                    title="📅 Scheduled Messages Commands",
                    description="Schedule announcements",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/schedule", value="Schedule a message to be sent later", inline=False)
                embed.add_field(name="/schedulelist", value="List all scheduled messages", inline=False)
                embed.add_field(name="/cancelschedule", value="Cancel a scheduled message", inline=False)
                
            elif category in ["music"]:
                embed = discord.Embed(
                    title="🎵 Music Commands",
                    description="Play music in voice channels",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/play", value="Play a song from YouTube", inline=False)
                embed.add_field(name="/pause", value="Pause the current song", inline=False)
                embed.add_field(name="/resume", value="Resume playback", inline=False)
                embed.add_field(name="/skip", value="Skip to the next song", inline=False)
                embed.add_field(name="/stop", value="Stop playback and clear queue", inline=False)
                embed.add_field(name="/queue", value="View the music queue", inline=False)
                embed.add_field(name="/volume", value="Adjust the volume", inline=False)
                embed.add_field(name="/loop", value="Toggle loop mode", inline=False)
                embed.add_field(name="/nowplaying", value="Show the current song", inline=False)
                embed.add_field(name="/join", value="Join your voice channel", inline=False)
                embed.add_field(name="/leave", value="Leave the voice channel", inline=False)
                
            elif category in ["ticket", "tickets", "support"]:
                embed = discord.Embed(
                    title="🎫 Ticket Commands",
                    description="User support ticket system",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/ticketpanel", value="Create a panel for users to open tickets", inline=False)
                embed.add_field(name="/ticketsetup", value="Configure ticket system settings", inline=False)
                embed.add_field(name="/addsupportrole", value="Add a role to the support team", inline=False)
                embed.add_field(name="/removesupportrole", value="Remove a role from the support team", inline=False)
                
            else:
                # Category not found
                embed = discord.Embed(
                    title="Help: Category not found",
                    description=f"Category '{category}' was not found. Use `/help` to see all categories.",
                    color=discord.Color.red()
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utility(bot)) 