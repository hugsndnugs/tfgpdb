import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/welcome_config.json"
        self.ensure_data_folder()
        self.config = self.load_config()
        
    def ensure_data_folder(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.config_file):
            with open(self.config_file, "w") as f:
                json.dump({}, f)
                
    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
            
    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)
            
    def get_guild_config(self, guild_id):
        guild_id = str(guild_id)
        if guild_id not in self.config:
            self.config[guild_id] = {
                "welcome_channel": None,
                "welcome_message": "Welcome {user} to {server}! You are member #{count}.",
                "goodbye_channel": None,
                "goodbye_message": "Goodbye {user}! We'll miss you.",
                "welcome_dm": False,
                "welcome_dm_message": "Welcome to {server}! We hope you enjoy your stay."
            }
            self.save_config()
        return self.config[guild_id]
            
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        config = self.get_guild_config(guild_id)
        
        # Skip if welcome channel is not set
        if not config["welcome_channel"]:
            return
            
        channel = member.guild.get_channel(int(config["welcome_channel"]))
        if not channel:
            return
            
        # Format welcome message
        member_count = len([m for m in member.guild.members if not m.bot])
        message = config["welcome_message"].format(
            user=member.mention,
            server=member.guild.name,
            count=member_count
        )
        
        # Create an embed for the welcome message
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=message,
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Add user avatar
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        # Add account creation date
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=False
        )
        
        await channel.send(embed=embed)
        
        # Send DM if enabled
        if config["welcome_dm"]:
            dm_message = config["welcome_dm_message"].format(
                user=member.name,
                server=member.guild.name
            )
            
            try:
                await member.send(dm_message)
            except discord.Forbidden:
                # Can't send DM to the user
                pass
                
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = str(member.guild.id)
        config = self.get_guild_config(guild_id)
        
        # Skip if goodbye channel is not set
        if not config["goodbye_channel"]:
            return
            
        channel = member.guild.get_channel(int(config["goodbye_channel"]))
        if not channel:
            return
            
        # Format goodbye message
        message = config["goodbye_message"].format(
            user=member.mention,
            server=member.guild.name
        )
        
        # Create an embed for the goodbye message
        embed = discord.Embed(
            title="Member Left",
            description=message,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Add user avatar
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
            
        # Add join date if available
        if member.joined_at:
            days_ago = (datetime.now() - member.joined_at).days
            embed.add_field(
                name="Joined Server",
                value=f"{days_ago} days ago",
                inline=False
            )
            
        await channel.send(embed=embed)
        
    @app_commands.command(name="setwelcomechannel", description="Set the channel for welcome messages")
    @app_commands.describe(channel="The channel to send welcome messages to")
    @app_commands.default_permissions(manage_guild=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["welcome_channel"] = str(channel.id)
        self.save_config()
        
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}!")
        
    @app_commands.command(name="setgoodbyechannel", description="Set the channel for goodbye messages")
    @app_commands.describe(channel="The channel to send goodbye messages to")
    @app_commands.default_permissions(manage_guild=True)
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["goodbye_channel"] = str(channel.id)
        self.save_config()
        
        await interaction.response.send_message(f"Goodbye channel set to {channel.mention}!")
        
    @app_commands.command(name="setwelcomemessage", description="Set the welcome message")
    @app_commands.describe(message="The welcome message. Use {user}, {server}, {count} as placeholders.")
    @app_commands.default_permissions(manage_guild=True)
    async def set_welcome_message(self, interaction: discord.Interaction, message: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["welcome_message"] = message
        self.save_config()
        
        # Preview the message
        preview = message.format(
            user=interaction.user.mention,
            server=interaction.guild.name,
            count=len(interaction.guild.members)
        )
        
        await interaction.response.send_message(f"Welcome message set! Preview:\n{preview}")
        
    @app_commands.command(name="setgoodbyemessage", description="Set the goodbye message")
    @app_commands.describe(message="The goodbye message. Use {user}, {server} as placeholders.")
    @app_commands.default_permissions(manage_guild=True)
    async def set_goodbye_message(self, interaction: discord.Interaction, message: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["goodbye_message"] = message
        self.save_config()
        
        # Preview the message
        preview = message.format(
            user=interaction.user.mention,
            server=interaction.guild.name
        )
        
        await interaction.response.send_message(f"Goodbye message set! Preview:\n{preview}")
        
    @app_commands.command(name="togglewelcomedm", description="Toggle sending welcome DMs to new members")
    @app_commands.default_permissions(manage_guild=True)
    async def toggle_welcome_dm(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["welcome_dm"] = not config["welcome_dm"]
        self.save_config()
        
        status = "enabled" if config["welcome_dm"] else "disabled"
        await interaction.response.send_message(f"Welcome DMs {status}!")
        
    @app_commands.command(name="setwelcomedmmessage", description="Set the welcome DM message")
    @app_commands.describe(message="The welcome DM message. Use {user}, {server} as placeholders.")
    @app_commands.default_permissions(manage_guild=True)
    async def set_welcome_dm_message(self, interaction: discord.Interaction, message: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["welcome_dm_message"] = message
        self.save_config()
        
        # Preview the message
        preview = message.format(
            user=interaction.user.name,
            server=interaction.guild.name
        )
        
        await interaction.response.send_message(f"Welcome DM message set! Preview:\n{preview}")

async def setup(bot):
    await bot.add_cog(Welcome(bot)) 