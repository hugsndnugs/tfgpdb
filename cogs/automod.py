import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/automod_config.json"
        self.ensure_data_folder()
        self.config = self.load_config()
        
        # Message tracking for anti-spam
        self.user_message_times = defaultdict(lambda: deque(maxlen=10))
        self.user_mention_counts = defaultdict(lambda: deque(maxlen=10))
        
        # Default bad words list (can be customized per server)
        self.default_bad_words = [
            "badword1", "badword2", "badword3"  # Replace with actual bad words
        ]
        
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
                "enabled": False,
                "log_channel": None,
                "anti_spam": {
                    "enabled": True,
                    "max_messages": 5,  # Max messages in time frame
                    "time_frame": 3,    # Time frame in seconds
                    "punishment": "mute",
                    "punishment_duration": 5  # Minutes
                },
                "anti_mention": {
                    "enabled": True,
                    "max_mentions": 5,  # Max mentions in a single message
                    "punishment": "mute",
                    "punishment_duration": 5  # Minutes
                },
                "word_filter": {
                    "enabled": True,
                    "filtered_words": self.default_bad_words,
                    "punishment": "delete",  # delete, warn, mute, kick, ban
                },
                "invite_filter": {
                    "enabled": True,
                    "allowed_servers": [],  # List of allowed server IDs
                    "punishment": "delete"
                }
            }
            self.save_config()
        return self.config[guild_id]
            
    async def log_action(self, guild, action, user, reason, duration=None):
        config = self.get_guild_config(guild.id)
        if not config["log_channel"]:
            return
            
        log_channel = guild.get_channel(int(config["log_channel"]))
        if not log_channel:
            return
            
        embed = discord.Embed(
            title="AutoMod Action",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if duration:
            embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
            
        await log_channel.send(embed=embed)
        
    async def apply_punishment(self, message, config_section, reason):
        punishment = config_section["punishment"]
        
        if punishment == "delete":
            try:
                await message.delete()
                return "deleted message"
            except discord.NotFound:
                pass
                
        elif punishment == "warn":
            try:
                await message.channel.send(f"{message.author.mention} Warning: {reason}", delete_after=10)
                return "warned"
            except:
                pass
                
        elif punishment == "mute":
            # Get the muted role
            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                # Create muted role
                try:
                    muted_role = await message.guild.create_role(name="Muted")
                    # Set permissions
                    for channel in message.guild.channels:
                        await channel.set_permissions(muted_role, speak=False, send_messages=False)
                except:
                    return "failed to mute (couldn't create role)"
            
            duration = config_section.get("punishment_duration", 5)  # Default 5 minutes
            try:
                await message.delete()
                await message.author.add_roles(muted_role, reason=reason)
                
                # Schedule unmute
                await asyncio.sleep(duration * 60)
                try:
                    await message.author.remove_roles(muted_role)
                except:
                    pass
                    
                return f"muted for {duration} minutes"
            except:
                return "failed to mute"
                
        elif punishment == "kick":
            try:
                await message.guild.kick(message.author, reason=reason)
                return "kicked"
            except:
                return "failed to kick"
                
        elif punishment == "ban":
            try:
                await message.guild.ban(message.author, reason=reason, delete_message_days=1)
                return "banned"
            except:
                return "failed to ban"
                
        return "no action taken"
        
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore DMs and bot messages
        if not message.guild or message.author.bot:
            return
            
        guild_id = str(message.guild.id)
        config = self.get_guild_config(guild_id)
        
        # Skip if automod is disabled for this guild
        if not config["enabled"]:
            return
            
        # Check for spam
        if config["anti_spam"]["enabled"]:
            key = f"{guild_id}:{message.author.id}"
            now = datetime.now()
            self.user_message_times[key].append(now)
            
            # Check if user sent too many messages in the time frame
            time_frame = config["anti_spam"]["time_frame"]
            max_messages = config["anti_spam"]["max_messages"]
            
            # Only check if they've sent at least max_messages
            if len(self.user_message_times[key]) >= max_messages:
                # Get the oldest message time in our window
                oldest = self.user_message_times[key][0]
                
                # If the time difference is less than the time frame, it's spam
                if (now - oldest).total_seconds() < time_frame:
                    reason = f"Sending messages too quickly ({max_messages} in {time_frame}s)"
                    action = await self.apply_punishment(message, config["anti_spam"], reason)
                    await self.log_action(
                        message.guild, 
                        action, 
                        message.author, 
                        reason,
                        config["anti_spam"].get("punishment_duration")
                    )
                    return  # Stop processing this message
            
        # Check for mention spam
        if config["anti_mention"]["enabled"] and message.mentions:
            max_mentions = config["anti_mention"]["max_mentions"]
            if len(message.mentions) > max_mentions:
                reason = f"Too many mentions in one message ({len(message.mentions)})"
                action = await self.apply_punishment(message, config["anti_mention"], reason)
                await self.log_action(
                    message.guild,
                    action,
                    message.author,
                    reason,
                    config["anti_mention"].get("punishment_duration")
                )
                return  # Stop processing
                
        # Check for bad words
        if config["word_filter"]["enabled"]:
            content = message.content.lower()
            for word in config["word_filter"]["filtered_words"]:
                pattern = r'\b' + re.escape(word.lower()) + r'\b'
                if re.search(pattern, content):
                    reason = f"Filtered word detected: {word}"
                    action = await self.apply_punishment(message, config["word_filter"], reason)
                    await self.log_action(message.guild, action, message.author, reason)
                    return  # Stop processing
                    
        # Check for Discord invites
        if config["invite_filter"]["enabled"]:
            invite_pattern = r'discord(?:\.gg|app\.com\/invite|\.com\/invite)\/([a-zA-Z0-9\-]{2,})'
            invites = re.findall(invite_pattern, message.content)
            
            if invites:
                # If no allowed servers are specified, block all invites
                if not config["invite_filter"]["allowed_servers"]:
                    reason = "Discord invite link not allowed"
                    action = await self.apply_punishment(message, config["invite_filter"], reason)
                    await self.log_action(message.guild, action, message.author, reason)
                    return
                
                # Check each invite
                for invite_code in invites:
                    try:
                        invite = await self.bot.fetch_invite(invite_code)
                        if str(invite.guild.id) not in config["invite_filter"]["allowed_servers"]:
                            reason = f"Invite to non-allowed server: {invite.guild.name}"
                            action = await self.apply_punishment(message, config["invite_filter"], reason)
                            await self.log_action(message.guild, action, message.author, reason)
                            return
                    except:
                        # If we can't fetch the invite, assume it's not allowed
                        reason = "Discord invite link not allowed (could not verify server)"
                        action = await self.apply_punishment(message, config["invite_filter"], reason)
                        await self.log_action(message.guild, action, message.author, reason)
                        return
                        
    @app_commands.command(name="automod", description="Toggle automod on/off")
    @app_commands.default_permissions(manage_guild=True)
    async def toggle_automod(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["enabled"] = not config["enabled"]
        self.save_config()
        
        status = "enabled" if config["enabled"] else "disabled"
        await interaction.response.send_message(f"AutoMod {status}!")

    @app_commands.command(name="automodlog", description="Set the channel for automod logs")
    @app_commands.describe(channel="The channel to send automod logs to")
    @app_commands.default_permissions(manage_guild=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        config["log_channel"] = str(channel.id)
        self.save_config()
        
        await interaction.response.send_message(f"AutoMod log channel set to {channel.mention}!")
        
    @app_commands.command(name="addfilterword", description="Add a word to the filter")
    @app_commands.describe(word="The word to filter")
    @app_commands.default_permissions(manage_guild=True)
    async def add_filter_word(self, interaction: discord.Interaction, word: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        word = word.lower()
        if word in config["word_filter"]["filtered_words"]:
            await interaction.response.send_message(f"'{word}' is already in the filter!", ephemeral=True)
            return
            
        config["word_filter"]["filtered_words"].append(word)
        self.save_config()
        
        await interaction.response.send_message(f"Added '{word}' to the filter!", ephemeral=True)
        
    @app_commands.command(name="removefilterword", description="Remove a word from the filter")
    @app_commands.describe(word="The word to remove from the filter")
    @app_commands.default_permissions(manage_guild=True)
    async def remove_filter_word(self, interaction: discord.Interaction, word: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        word = word.lower()
        if word not in config["word_filter"]["filtered_words"]:
            await interaction.response.send_message(f"'{word}' is not in the filter!", ephemeral=True)
            return
            
        config["word_filter"]["filtered_words"].remove(word)
        self.save_config()
        
        await interaction.response.send_message(f"Removed '{word}' from the filter!", ephemeral=True)
        
    @app_commands.command(name="filterwords", description="List all filtered words")
    @app_commands.default_permissions(manage_guild=True)
    async def list_filter_words(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        words = config["word_filter"]["filtered_words"]
        if not words:
            await interaction.response.send_message("No words are being filtered.", ephemeral=True)
            return
            
        # Format as a list
        word_list = "\n".join([f"• {word}" for word in words])
        
        # Create an embed for the list
        embed = discord.Embed(
            title="Filtered Words",
            description=word_list,
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="allowserver", description="Allow invites from a specific server")
    @app_commands.describe(server_id="The ID of the server to allow invites from")
    @app_commands.default_permissions(manage_guild=True)
    async def allow_server(self, interaction: discord.Interaction, server_id: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        if server_id in config["invite_filter"]["allowed_servers"]:
            await interaction.response.send_message(f"Server ID {server_id} is already allowed!", ephemeral=True)
            return
            
        config["invite_filter"]["allowed_servers"].append(server_id)
        self.save_config()
        
        await interaction.response.send_message(f"Added server ID {server_id} to allowed servers!", ephemeral=True)
        
    @app_commands.command(name="disallowserver", description="Remove a server from the allowed invites list")
    @app_commands.describe(server_id="The ID of the server to disallow invites from")
    @app_commands.default_permissions(manage_guild=True)
    async def disallow_server(self, interaction: discord.Interaction, server_id: str):
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        if server_id not in config["invite_filter"]["allowed_servers"]:
            await interaction.response.send_message(f"Server ID {server_id} is not in the allowed list!", ephemeral=True)
            return
            
        config["invite_filter"]["allowed_servers"].remove(server_id)
        self.save_config()
        
        await interaction.response.send_message(f"Removed server ID {server_id} from allowed servers!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMod(bot)) 