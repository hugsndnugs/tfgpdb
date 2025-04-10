import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self.load_giveaways()
        
    def load_giveaways(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            if os.path.exists('data/giveaways.json'):
                with open('data/giveaways.json', 'r') as f:
                    data = json.load(f)
                    
                    # Convert string keys to int (Discord IDs are stored as strings in JSON)
                    self.active_giveaways = {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Error loading giveaways data: {e}")
            self.active_giveaways = {}
    
    def save_giveaways(self):
        if not os.path.exists('data'):
            os.makedirs('data')
            
        try:
            with open('data/giveaways.json', 'w') as f:
                # Convert int keys to strings for JSON serialization
                data = {str(k): v for k, v in self.active_giveaways.items()}
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving giveaways data: {e}")
    
    @app_commands.command(name="giveaway", description="Start a new giveaway")
    @app_commands.describe(
        prize="The prize to be given away",
        winners="Number of winners (default: 1)",
        duration="Duration in minutes (default: 60)",
        description="Additional description about the giveaway (optional)"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(self, interaction: discord.Interaction, prize: str, winners: Optional[int] = 1, 
                      duration: Optional[int] = 60, description: Optional[str] = None):
        # Validate inputs
        if winners < 1 or winners > 20:
            await interaction.response.send_message(
                "Number of winners must be between 1 and 20.", 
                ephemeral=True
            )
            return
            
        if duration < 1 or duration > 40320:  # Max 4 weeks (40320 minutes)
            await interaction.response.send_message(
                "Giveaway duration must be between 1 minute and 4 weeks (40320 minutes).", 
                ephemeral=True
            )
            return
            
        # Create giveaway embed
        end_time = datetime.now() + timedelta(minutes=duration)
        
        embed = discord.Embed(
            title=f"🎉 GIVEAWAY: {prize}",
            description=description or f"React with 🎉 to enter!",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Prize", value=prize, inline=True)
        embed.add_field(name="Winners", value=str(winners), inline=True)
        embed.add_field(name="Hosted by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Ends at", value=f"<t:{int(end_time.timestamp())}:F>", inline=False)
        embed.set_footer(text=f"Ends at • {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')} • Giveaway ID: {interaction.id}")
        
        await interaction.response.send_message("Creating giveaway...", ephemeral=True)
        giveaway_message = await interaction.channel.send(embed=embed)
        
        # Add reaction
        await giveaway_message.add_reaction("🎉")
        
        # Store the giveaway
        self.active_giveaways[giveaway_message.id] = {
            'message_id': giveaway_message.id,
            'channel_id': giveaway_message.channel.id,
            'guild_id': interaction.guild.id,
            'prize': prize,
            'description': description,
            'winners': winners,
            'host_id': interaction.user.id,
            'end_time': end_time.timestamp(),
            'ended': False
        }
        
        self.save_giveaways()
        
        # Schedule the giveaway to end
        self.bot.loop.create_task(self.end_giveaway_after(giveaway_message.id, duration * 60))
    
    @app_commands.command(name="giveaway_end", description="End a giveaway early")
    @app_commands.describe(
        message_id="The ID of the giveaway message to end"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_end(self, interaction: discord.Interaction, message_id: str):
        try:
            giveaway_id = int(message_id)
            
            # Check if giveaway exists
            if giveaway_id not in self.active_giveaways:
                await interaction.response.send_message(
                    "Giveaway not found. Make sure you're using the correct message ID.", 
                    ephemeral=True
                )
                return
                
            # Check if giveaway already ended
            if self.active_giveaways[giveaway_id].get('ended', False):
                await interaction.response.send_message(
                    "This giveaway has already ended.", 
                    ephemeral=True
                )
                return
                
            await interaction.response.send_message(
                "Ending giveaway...", 
                ephemeral=True
            )
            
            # End the giveaway
            await self.end_giveaway(giveaway_id)
            
        except ValueError:
            await interaction.response.send_message(
                "Invalid message ID. Please provide a valid number.", 
                ephemeral=True
            )
    
    @app_commands.command(name="giveaway_reroll", description="Reroll the winners of an ended giveaway")
    @app_commands.describe(
        message_id="The ID of the giveaway message to reroll",
        winners="Number of new winners to select (default: 1)"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str, winners: Optional[int] = 1):
        try:
            giveaway_id = int(message_id)
            
            # Check if giveaway exists
            if giveaway_id not in self.active_giveaways:
                await interaction.response.send_message(
                    "Giveaway not found. Make sure you're using the correct message ID.", 
                    ephemeral=True
                )
                return
                
            # Check if giveaway has ended
            if not self.active_giveaways[giveaway_id].get('ended', False):
                await interaction.response.send_message(
                    "This giveaway has not ended yet. End it first before rerolling.", 
                    ephemeral=True
                )
                return
                
            # Validate winners count
            if winners < 1 or winners > 20:
                await interaction.response.send_message(
                    "Number of winners must be between 1 and 20.", 
                    ephemeral=True
                )
                return
                
            await interaction.response.send_message(
                "Rerolling giveaway winners...", 
                ephemeral=True
            )
            
            # Reroll the giveaway
            await self.reroll_giveaway(giveaway_id, winners)
            
        except ValueError:
            await interaction.response.send_message(
                "Invalid message ID. Please provide a valid number.", 
                ephemeral=True
            )
    
    @app_commands.command(name="giveaway_list", description="List all active giveaways")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_list(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        
        # Filter giveaways for this guild
        guild_giveaways = {msg_id: data for msg_id, data in self.active_giveaways.items() 
                          if data.get('guild_id') == guild_id and not data.get('ended', False)}
        
        if not guild_giveaways:
            await interaction.response.send_message(
                "There are no active giveaways in this server.", 
                ephemeral=True
            )
            return
            
        # Create embed
        embed = discord.Embed(
            title="Active Giveaways",
            description=f"There are {len(guild_giveaways)} active giveaways in this server.",
            color=discord.Color.green()
        )
        
        for msg_id, data in guild_giveaways.items():
            end_time = datetime.fromtimestamp(data['end_time'])
            time_left = end_time - datetime.now()
            
            # Format time left nicely
            days, remainder = divmod(time_left.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            time_str = ""
            if days > 0:
                time_str += f"{int(days)}d "
            if hours > 0 or days > 0:
                time_str += f"{int(hours)}h "
            if minutes > 0 or hours > 0 or days > 0:
                time_str += f"{int(minutes)}m "
            time_str += f"{int(seconds)}s"
            
            channel = self.bot.get_channel(data['channel_id'])
            channel_name = channel.name if channel else "Unknown Channel"
            
            embed.add_field(
                name=f"🎉 {data['prize']}",
                value=f"**Channel:** {channel_name}\n"
                      f"**Winners:** {data['winners']}\n"
                      f"**Ends in:** {time_str}\n"
                      f"**Message ID:** {msg_id}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def end_giveaway_after(self, giveaway_id, seconds):
        await asyncio.sleep(seconds)
        await self.end_giveaway(giveaway_id)
    
    async def end_giveaway(self, giveaway_id):
        # Check if giveaway exists and hasn't ended yet
        if giveaway_id not in self.active_giveaways or self.active_giveaways[giveaway_id].get('ended', False):
            return
            
        giveaway = self.active_giveaways[giveaway_id]
        
        try:
            # Get the channel and message
            channel = self.bot.get_channel(giveaway['channel_id'])
            if not channel:
                channel = await self.bot.fetch_channel(giveaway['channel_id'])
                
            message = await channel.fetch_message(giveaway_id)
            
            # Get the reaction
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            
            if not reaction:
                await channel.send(f"Could not end the giveaway for {giveaway['prize']} because the reaction was removed.")
                giveaway['ended'] = True
                self.save_giveaways()
                return
            
            # Get all users who reacted (excluding the bot)
            users = []
            async for user in reaction.users():
                if user.id != self.bot.user.id:
                    users.append(user)
            
            # Check if enough users participated
            if len(users) < giveaway['winners']:
                await channel.send(f"Not enough participants for the giveaway of **{giveaway['prize']}**. Needed {giveaway['winners']} participants, but only got {len(users)}.")
                giveaway['ended'] = True
                self.save_giveaways()
                return
            
            # Get the winners
            winners = random.sample(users, giveaway['winners'])
            winners_mentions = [winner.mention for winner in winners]
            
            # Update the giveaway embed
            embed = message.embeds[0]
            embed.color = discord.Color.dark_gray()
            embed.description = "**Giveaway Ended**\n\n" + (giveaway['description'] or "")
            embed.set_footer(text=f"Ended at • {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} • Giveaway ID: {giveaway_id}")
            
            await message.edit(embed=embed)
            
            # Send the winners message
            winners_message = await channel.send(
                f"🎉 **GIVEAWAY ENDED** 🎉\n\n"
                f"**Prize:** {giveaway['prize']}\n"
                f"**Winners:** {', '.join(winners_mentions)}\n\n"
                f"Congratulations! Contact {self.bot.get_user(giveaway['host_id']).mention} to claim your prize."
            )
            
            # Update the giveaway in the database
            giveaway['ended'] = True
            giveaway['winners_ids'] = [winner.id for winner in winners]
            giveaway['winners_message_id'] = winners_message.id
            self.save_giveaways()
            
        except Exception as e:
            print(f"Error ending giveaway {giveaway_id}: {e}")
            
            # Mark as ended anyway to avoid repeated failures
            giveaway['ended'] = True
            self.save_giveaways()
    
    async def reroll_giveaway(self, giveaway_id, num_winners):
        # Check if giveaway exists and has ended
        if giveaway_id not in self.active_giveaways or not self.active_giveaways[giveaway_id].get('ended', False):
            return
            
        giveaway = self.active_giveaways[giveaway_id]
        
        try:
            # Get the channel and message
            channel = self.bot.get_channel(giveaway['channel_id'])
            if not channel:
                channel = await self.bot.fetch_channel(giveaway['channel_id'])
                
            message = await channel.fetch_message(giveaway_id)
            
            # Get the reaction
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            
            if not reaction:
                await channel.send(f"Could not reroll the giveaway for {giveaway['prize']} because the reaction was removed.")
                return
            
            # Get all users who reacted (excluding the bot)
            users = []
            async for user in reaction.users():
                if user.id != self.bot.user.id:
                    users.append(user)
            
            # Check if enough users participated
            if len(users) < num_winners:
                await channel.send(f"Not enough participants for rerolling the giveaway of **{giveaway['prize']}**. Needed {num_winners} participants, but only got {len(users)}.")
                return
            
            # Get the new winners
            winners = random.sample(users, num_winners)
            winners_mentions = [winner.mention for winner in winners]
            
            # Send the reroll winners message
            await channel.send(
                f"🎉 **GIVEAWAY REROLLED** 🎉\n\n"
                f"**Prize:** {giveaway['prize']}\n"
                f"**New Winners:** {', '.join(winners_mentions)}\n\n"
                f"Congratulations! Contact {self.bot.get_user(giveaway['host_id']).mention} to claim your prize."
            )
            
        except Exception as e:
            print(f"Error rerolling giveaway {giveaway_id}: {e}")
    
    async def cog_load(self):
        """Tasks to run when the cog is loaded"""
        self.bot.loop.create_task(self.check_giveaways())
        
    async def check_giveaways(self):
        """Check for and end expired giveaways"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            current_time = datetime.now().timestamp()
            giveaways_to_end = []
            
            for giveaway_id, data in self.active_giveaways.items():
                if not data.get('ended', False) and current_time >= data['end_time']:
                    giveaways_to_end.append(giveaway_id)
            
            for giveaway_id in giveaways_to_end:
                await self.end_giveaway(giveaway_id)
            
            # Check every minute
            await asyncio.sleep(60)

async def setup(bot):
    await bot.add_cog(Giveaways(bot)) 