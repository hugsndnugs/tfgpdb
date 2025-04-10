import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta

class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}
        self.load_active_polls()
        
    def load_active_polls(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            if os.path.exists('data/polls.json'):
                with open('data/polls.json', 'r') as f:
                    data = json.load(f)
                    
                    # Convert string keys to int (Discord IDs are stored as strings in JSON)
                    self.active_polls = {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Error loading polls data: {e}")
            self.active_polls = {}
    
    def save_active_polls(self):
        if not os.path.exists('data'):
            os.makedirs('data')
            
        try:
            with open('data/polls.json', 'w') as f:
                # Convert int keys to strings for JSON serialization
                data = {str(k): v for k, v in self.active_polls.items()}
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving polls data: {e}")
    
    @app_commands.command(name="poll", description="Create a simple poll with up to 9 options")
    @app_commands.describe(
        question="The question for your poll",
        option1="Option 1",
        option2="Option 2",
        option3="Option 3 (optional)",
        option4="Option 4 (optional)",
        option5="Option 5 (optional)",
        option6="Option 6 (optional)",
        option7="Option 7 (optional)",
        option8="Option 8 (optional)",
        option9="Option 9 (optional)",
        duration="Poll duration in minutes (default: 60)"
    )
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, 
                  option3: str = None, option4: str = None, option5: str = None,
                  option6: str = None, option7: str = None, option8: str = None, 
                  option9: str = None, duration: int = 60):
        # Check if duration is valid
        if duration < 1 or duration > 10080:  # Max 1 week (10080 minutes)
            await interaction.response.send_message(
                "Poll duration must be between 1 minute and 1 week (10080 minutes).", 
                ephemeral=True
            )
            return
        
        # Format options
        options = [opt for opt in [option1, option2, option3, option4, option5, 
                                   option6, option7, option8, option9] if opt]
        
        # Emoji list for options (maximum 9 options)
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
        
        # Create the poll embed
        embed = discord.Embed(
            title=f"📊 {question}",
            description="\n".join([f"{emojis[i]} {option}" for i, option in enumerate(options)]),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add footer with expiration time
        end_time = datetime.now() + timedelta(minutes=duration)
        embed.set_footer(text=f"Poll ends at {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await interaction.response.send_message("Creating poll...", ephemeral=True)
        poll_message = await interaction.channel.send(embed=embed)
        
        # Add reaction options
        for i in range(len(options)):
            await poll_message.add_reaction(emojis[i])
        
        # Store the poll in active polls
        self.active_polls[poll_message.id] = {
            'message_id': poll_message.id,
            'channel_id': poll_message.channel.id,
            'options': options,
            'emojis': emojis[:len(options)],
            'end_time': end_time.timestamp(),
            'question': question,
            'creator_id': interaction.user.id
        }
        
        self.save_active_polls()
        
        # Schedule the poll to end
        self.bot.loop.create_task(self.end_poll_after(poll_message.id, duration * 60))
    
    @app_commands.command(name="quickpoll", description="Create a simple yes/no poll")
    @app_commands.describe(
        question="The question for your yes/no poll",
        duration="Poll duration in minutes (default: 60)"
    )
    async def quickpoll(self, interaction: discord.Interaction, question: str, duration: int = 60):
        # Check if duration is valid
        if duration < 1 or duration > 10080:  # Max 1 week (10080 minutes)
            await interaction.response.send_message(
                "Poll duration must be between 1 minute and 1 week (10080 minutes).", 
                ephemeral=True
            )
            return
        
        # Create the poll embed
        embed = discord.Embed(
            title=f"📊 {question}",
            description="👍 Yes\n👎 No",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add footer with expiration time
        end_time = datetime.now() + timedelta(minutes=duration)
        embed.set_footer(text=f"Poll ends at {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await interaction.response.send_message("Creating poll...", ephemeral=True)
        poll_message = await interaction.channel.send(embed=embed)
        
        # Add reaction options
        await poll_message.add_reaction('👍')
        await poll_message.add_reaction('👎')
        
        # Store the poll in active polls
        self.active_polls[poll_message.id] = {
            'message_id': poll_message.id,
            'channel_id': poll_message.channel.id,
            'options': ['Yes', 'No'],
            'emojis': ['👍', '👎'],
            'end_time': end_time.timestamp(),
            'question': question,
            'creator_id': interaction.user.id
        }
        
        self.save_active_polls()
        
        # Schedule the poll to end
        self.bot.loop.create_task(self.end_poll_after(poll_message.id, duration * 60))
    
    @app_commands.command(name="endpoll", description="End a poll early and show results")
    @app_commands.describe(
        message_id="The ID of the poll message to end"
    )
    async def endpoll(self, interaction: discord.Interaction, message_id: str):
        try:
            poll_id = int(message_id)
            if poll_id not in self.active_polls:
                await interaction.response.send_message("Poll not found or already ended.", ephemeral=True)
                return
                
            poll_data = self.active_polls[poll_id]
            
            # Only the poll creator or admins can end polls early
            if interaction.user.id != poll_data['creator_id'] and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Only the poll creator or administrators can end polls early.", ephemeral=True)
                return
                
            await interaction.response.send_message("Ending poll...", ephemeral=True)
            await self.end_poll(poll_id)
            
        except ValueError:
            await interaction.response.send_message("Invalid message ID. Please provide a valid number.", ephemeral=True)
    
    async def end_poll_after(self, poll_id, seconds):
        await asyncio.sleep(seconds)
        await self.end_poll(poll_id)
    
    async def end_poll(self, poll_id):
        if poll_id not in self.active_polls:
            return
            
        poll_data = self.active_polls[poll_id]
        
        try:
            channel = self.bot.get_channel(poll_data['channel_id'])
            if not channel:
                # Try to fetch the channel if it's not in cache
                channel = await self.bot.fetch_channel(poll_data['channel_id'])
                
            message = await channel.fetch_message(poll_id)
            
            # Count the votes
            votes = {}
            total_votes = 0
            
            for i, emoji in enumerate(poll_data['emojis']):
                reaction = discord.utils.get(message.reactions, emoji=emoji)
                count = reaction.count - 1  # Subtract 1 to exclude bot's reaction
                if count < 0:
                    count = 0
                votes[poll_data['options'][i]] = count
                total_votes += count
            
            # Create results embed
            embed = discord.Embed(
                title=f"📊 Poll Results: {poll_data['question']}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Format the results
            results = []
            for option, count in votes.items():
                percentage = 0 if total_votes == 0 else round((count / total_votes) * 100)
                bar = '█' * int(percentage / 10) + '░' * (10 - int(percentage / 10))
                results.append(f"{option}: {bar} {count} votes ({percentage}%)")
            
            embed.description = "\n".join(results)
            embed.set_footer(text=f"Total votes: {total_votes}")
            
            await channel.send(embed=embed)
            
            # Update the original poll to show it has ended
            original_embed = message.embeds[0]
            original_embed.color = discord.Color.dark_gray()
            original_embed.set_footer(text="Poll ended")
            await message.edit(embed=original_embed)
            
            # Remove from active polls
            del self.active_polls[poll_id]
            self.save_active_polls()
            
        except Exception as e:
            print(f"Error ending poll {poll_id}: {e}")
            # Clean up if we couldn't process it
            if poll_id in self.active_polls:
                del self.active_polls[poll_id]
                self.save_active_polls()
                
    async def cog_load(self):
        """Tasks to run when the cog is loaded"""
        self.bot.loop.create_task(self.check_expired_polls())
        
    async def check_expired_polls(self):
        """Check for and end expired polls"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            current_time = datetime.now().timestamp()
            polls_to_end = []
            
            for poll_id, poll_data in self.active_polls.items():
                if current_time >= poll_data['end_time']:
                    polls_to_end.append(poll_id)
            
            for poll_id in polls_to_end:
                await self.end_poll(poll_id)
            
            # Check every minute
            await asyncio.sleep(60)

async def setup(bot):
    await bot.add_cog(Polls(bot)) 