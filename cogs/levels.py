import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import os
from datetime import datetime, timedelta

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.levels_file = "data/levels.json"
        self.cooldowns = {}  # Store message cooldowns
        self.ensure_data_folder()
        self.levels = self.load_levels()

    def ensure_data_folder(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.levels_file):
            with open(self.levels_file, "w") as f:
                json.dump({}, f)

    def load_levels(self):
        try:
            with open(self.levels_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_levels(self):
        with open(self.levels_file, "w") as f:
            json.dump(self.levels, f, indent=4)

    def get_level_from_xp(self, xp):
        return int(xp ** 0.3)

    def get_xp_for_level(self, level):
        return int(level ** (1/0.3))

    def get_user_data(self, user_id, guild_id):
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        if guild_id not in self.levels:
            self.levels[guild_id] = {}
            
        if user_id not in self.levels[guild_id]:
            self.levels[guild_id][user_id] = {
                "xp": 0,
                "level": 0,
                "last_message": 0
            }
            
        return self.levels[guild_id][user_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't count bot messages or commands
        if message.author.bot or message.content.startswith(("!", "/")):
            return
            
        # Check cooldown (60 seconds)
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        cooldown_key = f"{guild_id}:{user_id}"
        
        current_time = datetime.now().timestamp()
        if cooldown_key in self.cooldowns:
            if current_time - self.cooldowns[cooldown_key] < 60:
                return  # Still on cooldown
                
        # Update cooldown
        self.cooldowns[cooldown_key] = current_time
        
        # Get user data
        user_data = self.get_user_data(user_id, guild_id)
        
        # Award XP (random between 15-25)
        xp_gained = random.randint(15, 25)
        old_level = user_data["level"]
        user_data["xp"] += xp_gained
        new_level = self.get_level_from_xp(user_data["xp"])
        user_data["level"] = new_level
        
        self.save_levels()
        
        # Check for level up
        if new_level > old_level:
            # Find a suitable channel to send the level up message
            channel = message.channel
            
            embed = discord.Embed(
                title="Level Up!",
                description=f"Congratulations {message.author.mention}! You've reached level **{new_level}**!",
                color=discord.Color.green()
            )
            
            await channel.send(embed=embed)

    @app_commands.command(name="rank", description="Check your or someone else's rank")
    @app_commands.describe(member="The member to check (leave empty for yourself)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        user_id = str(member.id)
        guild_id = str(interaction.guild.id)
        
        user_data = self.get_user_data(user_id, guild_id)
        current_xp = user_data["xp"]
        current_level = user_data["level"]
        
        # Calculate XP needed for next level
        next_level = current_level + 1
        xp_needed = self.get_xp_for_level(next_level)
        xp_progress = current_xp / xp_needed * 100 if xp_needed > 0 else 100
        
        # Create embed
        embed = discord.Embed(
            title=f"Rank for {member.display_name}",
            color=member.color
        )
        
        embed.add_field(name="Level", value=current_level, inline=True)
        embed.add_field(name="XP", value=f"{current_xp}/{xp_needed}", inline=True)
        embed.add_field(name="Progress to Next Level", value=f"{xp_progress:.1f}%", inline=True)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Show the server XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.levels or not self.levels[guild_id]:
            await interaction.followup.send("No one has earned XP on this server yet!")
            return
            
        # Sort users by XP
        sorted_users = sorted(
            self.levels[guild_id].items(),
            key=lambda x: x[1]["xp"],
            reverse=True
        )
        
        # Take top 10
        top_users = sorted_users[:10]
        
        # Create embed
        embed = discord.Embed(
            title=f"XP Leaderboard for {interaction.guild.name}",
            color=discord.Color.gold()
        )
        
        # Add fields for each user
        for i, (user_id, data) in enumerate(top_users, 1):
            # Try to get the user
            user = interaction.guild.get_member(int(user_id))
            name = user.display_name if user else f"Unknown User ({user_id})"
            
            embed.add_field(
                name=f"{i}. {name}",
                value=f"Level: {data['level']} | XP: {data['xp']}",
                inline=False
            )
            
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Levels(bot)) 