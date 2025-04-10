import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta
import re
from typing import Optional, Literal

class Schedules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedules = {}
        self.load_schedules()
        
    def load_schedules(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            if os.path.exists('data/schedules.json'):
                with open('data/schedules.json', 'r') as f:
                    data = json.load(f)
                    
                    # Convert string keys to int (Discord IDs are stored as strings in JSON)
                    self.schedules = {int(k): {int(s_id): s_data for s_id, s_data in v.items()} 
                                    for k, v in data.items()}
        except Exception as e:
            print(f"Error loading schedules data: {e}")
            self.schedules = {}
    
    def save_schedules(self):
        if not os.path.exists('data'):
            os.makedirs('data')
            
        try:
            with open('data/schedules.json', 'w') as f:
                # Convert int keys to strings for JSON serialization
                data = {str(k): {str(s_id): s_data for s_id, s_data in v.items()} 
                      for k, v in self.schedules.items()}
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving schedules data: {e}")
    
    def parse_time(self, time_str):
        """Parse a time string into a datetime object"""
        patterns = [
            # In X minutes/hours/days
            (r'in (\d+) minute(?:s)?', lambda m: datetime.now() + timedelta(minutes=int(m.group(1)))),
            (r'in (\d+) hour(?:s)?', lambda m: datetime.now() + timedelta(hours=int(m.group(1)))),
            (r'in (\d+) day(?:s)?', lambda m: datetime.now() + timedelta(days=int(m.group(1)))),
            
            # Every X minutes/hours/days
            (r'every (\d+) minute(?:s)?', lambda m: {'interval': int(m.group(1)) * 60, 'unit': 'minutes'}),
            (r'every (\d+) hour(?:s)?', lambda m: {'interval': int(m.group(1)) * 3600, 'unit': 'hours'}),
            (r'every (\d+) day(?:s)?', lambda m: {'interval': int(m.group(1)) * 86400, 'unit': 'days'}),
            
            # Time of day (HH:MM)
            (r'(\d{1,2}):(\d{2})', lambda m: self.next_time_at(int(m.group(1)), int(m.group(2)))),
            
            # Date and time (YYYY-MM-DD HH:MM)
            (r'(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2})', 
             lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 
                               int(m.group(4)), int(m.group(5))))
        ]
        
        for pattern, handler in patterns:
            match = re.match(pattern, time_str, re.IGNORECASE)
            if match:
                return handler(match)
                
        return None
    
    def next_time_at(self, hour, minute):
        """Get the next occurrence of a specific time"""
        now = datetime.now()
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_time <= now:
            next_time += timedelta(days=1)
            
        return next_time
    
    @app_commands.command(name="schedule", description="Schedule a message to be sent later")
    @app_commands.describe(
        channel="The channel to send the message in",
        time="When to send the message (e.g., 'in 10 minutes', '18:00', '2023-12-25 12:00')",
        message="The message to send",
        repeat="Whether the schedule should repeat (default: false)",
        embed="Whether to send the message as an embed (default: false)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def schedule(self, interaction: discord.Interaction, channel: discord.TextChannel, 
                      time: str, message: str, repeat: Optional[bool] = False, 
                      embed: Optional[bool] = False):
        # Parse the time
        parsed_time = self.parse_time(time)
        if not parsed_time:
            await interaction.response.send_message(
                "Invalid time format. Examples: 'in 10 minutes', 'every 2 hours', '18:00', '2023-12-25 12:00'", 
                ephemeral=True
            )
            return
            
        # Generate a unique ID for this schedule
        schedule_id = int(datetime.now().timestamp())
        guild_id = interaction.guild.id
        
        # Initialize guild schedules if not exists
        if guild_id not in self.schedules:
            self.schedules[guild_id] = {}
            
        # Create the schedule
        schedule_data = {
            'channel_id': channel.id,
            'message': message,
            'creator_id': interaction.user.id,
            'created_at': datetime.now().isoformat(),
            'use_embed': embed
        }
        
        if isinstance(parsed_time, dict):  # Repeating schedule
            if not repeat:
                await interaction.response.send_message(
                    f"You provided a repeating time format ('{time}') but didn't set repeat=True. "
                    f"Please use /schedule again with repeat=True if you want a repeating schedule.", 
                    ephemeral=True
                )
                return
                
            schedule_data.update({
                'repeat': True,
                'interval': parsed_time['interval'],
                'unit': parsed_time['unit'],
                'next_run': (datetime.now() + timedelta(seconds=parsed_time['interval'])).isoformat()
            })
            
            confirm_message = (f"Schedule created! I'll send your message to {channel.mention} "
                            f"every {parsed_time['interval'] // 60 if parsed_time['unit'] == 'minutes' else parsed_time['interval'] // 3600 if parsed_time['unit'] == 'hours' else parsed_time['interval'] // 86400} "
                            f"{parsed_time['unit']}.")
        else:  # One-time schedule
            if repeat:
                await interaction.response.send_message(
                    f"You set repeat=True but provided a one-time time format ('{time}'). "
                    f"For repeating schedules, use formats like 'every X minutes/hours/days'.", 
                    ephemeral=True
                )
                return
                
            schedule_data.update({
                'repeat': False,
                'run_at': parsed_time.isoformat()
            })
            
            confirm_message = f"Schedule created! I'll send your message to {channel.mention} at {parsed_time.strftime('%Y-%m-%d %H:%M:%S')}."
        
        # Store the schedule
        self.schedules[guild_id][schedule_id] = schedule_data
        self.save_schedules()
        
        # Schedule the message
        if not schedule_data['repeat']:
            # Calculate seconds until the scheduled time
            seconds_until = (parsed_time - datetime.now()).total_seconds()
            if seconds_until > 0:
                self.bot.loop.create_task(self.send_scheduled_message(guild_id, schedule_id, seconds_until))
        
        # Confirm to the user
        await interaction.response.send_message(
            f"{confirm_message}\nSchedule ID: `{schedule_id}`\n"
            f"Use `/schedulelist` to see all schedules or `/cancelschedule {schedule_id}` to cancel this schedule.", 
            ephemeral=True
        )
    
    @app_commands.command(name="schedulelist", description="List all scheduled messages")
    @app_commands.describe(
        show_all="Whether to show schedules for the entire server or just yours (requires manage_messages)"
    )
    async def schedulelist(self, interaction: discord.Interaction, show_all: Optional[bool] = False):
        guild_id = interaction.guild.id
        
        # Check if guild has any schedules
        if guild_id not in self.schedules or not self.schedules[guild_id]:
            await interaction.response.send_message(
                "There are no scheduled messages in this server.", 
                ephemeral=True
            )
            return
            
        # Filter schedules based on permissions
        user_is_admin = interaction.user.guild_permissions.manage_messages
        schedules_to_show = {}
        
        if show_all and user_is_admin:
            schedules_to_show = self.schedules[guild_id]
        else:
            schedules_to_show = {s_id: s_data for s_id, s_data in self.schedules[guild_id].items() 
                               if s_data['creator_id'] == interaction.user.id}
            
        if not schedules_to_show:
            await interaction.response.send_message(
                "You don't have any scheduled messages. Use /schedule to create one.", 
                ephemeral=True
            )
            return
            
        # Create embed
        embed = discord.Embed(
            title="Scheduled Messages",
            description=f"Found {len(schedules_to_show)} scheduled message(s).",
            color=discord.Color.blue()
        )
        
        for schedule_id, data in schedules_to_show.items():
            channel = self.bot.get_channel(data['channel_id'])
            channel_mention = channel.mention if channel else f"Unknown Channel ({data['channel_id']})"
            
            if data['repeat']:
                next_run = datetime.fromisoformat(data['next_run'])
                time_left = next_run - datetime.now()
                
                if time_left.total_seconds() < 0:
                    time_str = "Overdue (will run soon)"
                else:
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
                
                field_value = (
                    f"**Channel:** {channel_mention}\n"
                    f"**Next run:** {time_str}\n"
                    f"**Repeats:** Every {data['interval'] // 60 if data['unit'] == 'minutes' else data['interval'] // 3600 if data['unit'] == 'hours' else data['interval'] // 86400} {data['unit']}\n"
                    f"**Message:** {data['message'][:50]}{'...' if len(data['message']) > 50 else ''}\n"
                    f"**Format:** {'Embed' if data['use_embed'] else 'Plain text'}"
                )
            else:
                run_at = datetime.fromisoformat(data['run_at'])
                time_left = run_at - datetime.now()
                
                if time_left.total_seconds() < 0:
                    time_str = "Overdue (will run soon)"
                else:
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
                
                field_value = (
                    f"**Channel:** {channel_mention}\n"
                    f"**Runs in:** {time_str}\n"
                    f"**Date:** {run_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**Message:** {data['message'][:50]}{'...' if len(data['message']) > 50 else ''}\n"
                    f"**Format:** {'Embed' if data['use_embed'] else 'Plain text'}"
                )
            
            embed.add_field(
                name=f"Schedule ID: {schedule_id}",
                value=field_value,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cancelschedule", description="Cancel a scheduled message")
    @app_commands.describe(
        schedule_id="The ID of the schedule to cancel"
    )
    async def cancelschedule(self, interaction: discord.Interaction, schedule_id: str):
        try:
            s_id = int(schedule_id)
            guild_id = interaction.guild.id
            
            # Check if guild has any schedules
            if guild_id not in self.schedules or s_id not in self.schedules[guild_id]:
                await interaction.response.send_message(
                    "Schedule not found. Use /schedulelist to see all available schedules.", 
                    ephemeral=True
                )
                return
                
            # Check if user has permission to cancel this schedule
            schedule_data = self.schedules[guild_id][s_id]
            
            if schedule_data['creator_id'] != interaction.user.id and not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "You don't have permission to cancel this schedule. Only the creator or admins can cancel it.", 
                    ephemeral=True
                )
                return
                
            # Remove the schedule
            del self.schedules[guild_id][s_id]
            
            # Clean up if no more schedules for guild
            if not self.schedules[guild_id]:
                del self.schedules[guild_id]
                
            self.save_schedules()
            
            await interaction.response.send_message(
                f"Schedule {s_id} has been cancelled successfully.", 
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                "Invalid schedule ID. Please provide a valid number.", 
                ephemeral=True
            )
    
    async def send_scheduled_message(self, guild_id, schedule_id, delay=None):
        """Send a scheduled message after the specified delay"""
        if delay:
            await asyncio.sleep(delay)
            
        # Check if the schedule still exists
        if guild_id not in self.schedules or schedule_id not in self.schedules[guild_id]:
            return
            
        schedule_data = self.schedules[guild_id][schedule_id]
        
        try:
            # Get the channel
            channel = self.bot.get_channel(schedule_data['channel_id'])
            if not channel:
                channel = await self.bot.fetch_channel(schedule_data['channel_id'])
                
            # Send the message
            if schedule_data['use_embed']:
                embed = discord.Embed(
                    description=schedule_data['message'],
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
            else:
                await channel.send(schedule_data['message'])
                
            # Handle repeating schedules
            if schedule_data['repeat']:
                # Update next run time
                next_run = datetime.now() + timedelta(seconds=schedule_data['interval'])
                schedule_data['next_run'] = next_run.isoformat()
                self.save_schedules()
                
                # Schedule the next run
                self.bot.loop.create_task(
                    self.send_scheduled_message(guild_id, schedule_id, schedule_data['interval'])
                )
            else:
                # Remove one-time schedule after it runs
                del self.schedules[guild_id][schedule_id]
                
                # Clean up if no more schedules for guild
                if not self.schedules[guild_id]:
                    del self.schedules[guild_id]
                    
                self.save_schedules()
                
        except Exception as e:
            print(f"Error sending scheduled message {schedule_id}: {e}")
    
    async def cog_load(self):
        """Tasks to run when the cog is loaded"""
        self.bot.loop.create_task(self.restart_schedules())
        
    async def restart_schedules(self):
        """Restart all schedules after bot restart"""
        await self.bot.wait_until_ready()
        
        for guild_id, guild_schedules in list(self.schedules.items()):
            for schedule_id, data in list(guild_schedules.items()):
                try:
                    if data['repeat']:
                        # For repeating schedules
                        next_run = datetime.fromisoformat(data['next_run'])
                        delay = (next_run - datetime.now()).total_seconds()
                        
                        if delay < 0:  # If next run is in the past
                            # Run immediately and reset the schedule
                            self.bot.loop.create_task(self.send_scheduled_message(guild_id, schedule_id))
                        else:
                            # Schedule for the future
                            self.bot.loop.create_task(self.send_scheduled_message(guild_id, schedule_id, delay))
                    else:
                        # For one-time schedules
                        run_at = datetime.fromisoformat(data['run_at'])
                        delay = (run_at - datetime.now()).total_seconds()
                        
                        if delay < 0:  # If run time is in the past
                            # Run immediately
                            self.bot.loop.create_task(self.send_scheduled_message(guild_id, schedule_id))
                        else:
                            # Schedule for the future
                            self.bot.loop.create_task(self.send_scheduled_message(guild_id, schedule_id, delay))
                except Exception as e:
                    print(f"Error restarting schedule {schedule_id}: {e}")

async def setup(bot):
    await bot.add_cog(Schedules(bot)) 