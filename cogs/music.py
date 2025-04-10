import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import yt_dlp as youtube_dl
import os
from typing import Optional
from collections import deque
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('music')

# Configure youtube_dl options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.requester = None

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, requester=None):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            
            if 'entries' in data:
                # Take first item from a playlist
                data = data['entries'][0]
                
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            source = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
            audio_source = cls(source, data=data)
            audio_source.requester = requester
            return audio_source
        except Exception as e:
            logger.error(f"Error creating audio source: {e}")
            raise

class MusicPlayer:
    """A class to represent a music player for a guild."""
    
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog
        
        self.queue = deque()
        self.next = asyncio.Event()
        
        self.current = None
        self.volume = 0.5
        self.loop = False
        
        ctx.bot.loop.create_task(self.player_loop())
    
    async def player_loop(self):
        """Main player loop."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            self.next.clear()
            
            # Try to get a song and play it
            try:
                # If looping is enabled and we have a current song, add it back to the queue
                if self.loop and self.current:
                    self.queue.appendleft(self.current)
                    
                # Wait for the next song. If none arrive in the next minute, the player will disconnect
                try:
                    async with asyncio.timeout(60):  # Wait for 60 seconds
                        self.current = self.queue.popleft()
                except asyncio.TimeoutError:
                    # No music in an minute, disconnect
                    await self.stop()
                    return
                    
                self.current.source.volume = self.volume
                self.guild.voice_client.play(self.current.source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
                
                # Send the now playing embed
                await self.send_now_playing()
                
                # Wait for the song to finish
                await self.next.wait()
                
                # Clear the current after it's done playing (if not looping)
                if not self.loop:
                    self.current = None
                    
            except asyncio.CancelledError:
                # Player was stopped
                break
            except Exception as e:
                logger.error(f"Error in player loop: {e}")
                await self.channel.send(f"An error occurred: {str(e)}")
                continue
    
    async def send_now_playing(self):
        """Send a now playing embed for the current song."""
        if not self.current:
            return
            
        embed = discord.Embed(
            title="Now Playing",
            description=f"[{self.current.source.title}]({self.current.source.webpage_url})",
            color=discord.Color.blue()
        )
        
        # Add duration if available
        if self.current.source.duration:
            minutes, seconds = divmod(self.current.source.duration, 60)
            hours, minutes = divmod(minutes, 60)
            
            duration = f"{int(minutes):02d}:{int(seconds):02d}"
            if hours > 0:
                duration = f"{int(hours):02d}:{duration}"
                
            embed.add_field(name="Duration", value=duration, inline=True)
            
        # Add requester if available
        if self.current.requester:
            embed.add_field(name="Requested by", value=self.current.requester.display_name, inline=True)
            
        # Add thumbnail if available
        if self.current.source.thumbnail:
            embed.set_thumbnail(url=self.current.source.thumbnail)
            
        # Show loop status
        embed.add_field(name="Loop", value="Enabled" if self.loop else "Disabled", inline=True)
        
        # Show volume
        embed.add_field(name="Volume", value=f"{int(self.volume * 100)}%", inline=True)
        
        # Add queue info
        if self.queue:
            embed.add_field(name="Up Next", value=f"{len(self.queue)} songs in queue", inline=True)
            
        await self.channel.send(embed=embed)
    
    async def stop(self):
        """Stop the player and disconnect."""
        self.queue.clear()
        
        if self.guild.voice_client:
            await self.guild.voice_client.disconnect()
            
        self.current = None

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        
    def get_player(self, ctx):
        """Get or create a player for a guild."""
        player = self.players.get(ctx.guild.id)
        
        if not player:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
            
        return player
    
    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.followup.send("You need to be in a voice channel to use this command.")
            return
            
        voice_channel = interaction.user.voice.channel
        
        # Check if bot is already in a voice channel
        if interaction.guild.voice_client:
            # If bot is already in the user's channel
            if interaction.guild.voice_client.channel.id == voice_channel.id:
                await interaction.followup.send(f"I'm already in {voice_channel.mention}!")
                return
                
            # Move to the user's channel
            await interaction.guild.voice_client.move_to(voice_channel)
            await interaction.followup.send(f"Moved to {voice_channel.mention}!")
        else:
            # Join the user's channel
            await voice_channel.connect()
            await interaction.followup.send(f"Joined {voice_channel.mention}!")
    
    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel
        if not interaction.guild.voice_client:
            await interaction.followup.send("I'm not in a voice channel!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Stop the player
        player = self.players.get(interaction.guild.id)
        if player:
            await player.stop()
            
        # Remove the player from the players dict
        if interaction.guild.id in self.players:
            del self.players[interaction.guild.id]
            
        await interaction.followup.send("Left the voice channel and cleared the queue.")
    
    @app_commands.command(name="play", description="Play a song")
    @app_commands.describe(
        query="Song name or URL to play"
    )
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.followup.send("You need to be in a voice channel to use this command.")
            return
            
        voice_channel = interaction.user.voice.channel
        
        # Join the voice channel if not already in one
        if not interaction.guild.voice_client:
            await voice_channel.connect()
        elif interaction.guild.voice_client.channel.id != voice_channel.id:
            await interaction.guild.voice_client.move_to(voice_channel)
            
        # Create a player if one doesn't exist
        ctx = await self.bot.get_context(interaction)
        player = self.get_player(ctx)
        
        # Check if query is a URL or search term
        if not re.match(r'https?://(?:www\.)?.+', query):
            search_query = f"ytsearch:{query}"
        else:
            search_query = query
            
        # Send a temporary message
        await interaction.followup.send(f"Searching for `{query}`...")
        
        try:
            # Get the source
            source = await YTDLSource.from_url(search_query, loop=self.bot.loop, stream=True, requester=interaction.user)
            
            # Create a song object
            song = type('Song', (), {'source': source, 'requester': interaction.user})
            
            # Add the song to the queue
            player.queue.append(song)
            
            await interaction.followup.send(f"Added [{source.title}]({source.webpage_url}) to the queue.")
        except Exception as e:
            logger.error(f"Error playing song: {e}")
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
            await interaction.followup.send("Nothing is playing right now!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Skip the song
        interaction.guild.voice_client.stop()
        await interaction.followup.send("Skipped the current song.")
    
    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get the player
        player = self.players.get(interaction.guild.id)
        if not player or not player.queue:
            await interaction.followup.send("The queue is empty.")
            return
            
        # Create the queue embed
        embed = discord.Embed(
            title="Music Queue",
            color=discord.Color.blue()
        )
        
        # Add the current song
        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"[{player.current.source.title}]({player.current.source.webpage_url})",
                inline=False
            )
            
        # Add the queue
        queue_list = []
        for i, song in enumerate(player.queue, start=1):
            if i > 10:  # Limit to 10 songs
                queue_list.append(f"And {len(player.queue) - 10} more...")
                break
                
            queue_list.append(f"{i}. [{song.source.title}]({song.source.webpage_url})")
            
        if queue_list:
            embed.add_field(
                name="Up Next",
                value="\n".join(queue_list),
                inline=False
            )
            
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel and playing
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
            await interaction.followup.send("Nothing is playing right now!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Check if already paused
        if interaction.guild.voice_client.is_paused():
            await interaction.followup.send("The music is already paused!")
            return
            
        # Pause the music
        interaction.guild.voice_client.pause()
        await interaction.followup.send("Paused the music.")
    
    @app_commands.command(name="resume", description="Resume the current song")
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel and paused
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_paused():
            await interaction.followup.send("Nothing is paused right now!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Resume the music
        interaction.guild.voice_client.resume()
        await interaction.followup.send("Resumed the music.")
    
    @app_commands.command(name="volume", description="Set the volume (0-100)")
    @app_commands.describe(
        level="Volume level (0-100)"
    )
    async def volume(self, interaction: discord.Interaction, level: int):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel
        if not interaction.guild.voice_client:
            await interaction.followup.send("I'm not in a voice channel!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Check if volume is valid
        if level < 0 or level > 100:
            await interaction.followup.send("Volume must be between 0 and 100.")
            return
            
        # Get the player
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.followup.send("No active player found.")
            return
            
        # Set the volume
        volume = level / 100
        player.volume = volume
        
        if player.current:
            player.current.source.volume = volume
            
        await interaction.followup.send(f"Set the volume to {level}%")
    
    @app_commands.command(name="loop", description="Toggle loop mode")
    async def loop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel
        if not interaction.guild.voice_client:
            await interaction.followup.send("I'm not in a voice channel!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Get the player
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.followup.send("No active player found.")
            return
            
        # Toggle loop mode
        player.loop = not player.loop
        await interaction.followup.send(f"Loop mode: {'Enabled' if player.loop else 'Disabled'}")
    
    @app_commands.command(name="stop", description="Stop playing and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if bot is in a voice channel
        if not interaction.guild.voice_client:
            await interaction.followup.send("I'm not in a voice channel!")
            return
            
        # Check if user is in the same voice channel
        if not interaction.user.voice or interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id:
            await interaction.followup.send("You need to be in the same voice channel as me to use this command.")
            return
            
        # Get the player
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.followup.send("No active player found.")
            return
            
        # Clear the queue and stop playing
        player.queue.clear()
        interaction.guild.voice_client.stop()
        await interaction.followup.send("Stopped the music and cleared the queue.")
    
    @app_commands.command(name="nowplaying", description="Show info about the current song")
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get the player
        player = self.players.get(interaction.guild.id)
        if not player or not player.current:
            await interaction.followup.send("Nothing is playing right now!")
            return
            
        # Create now playing embed
        embed = discord.Embed(
            title="Now Playing",
            description=f"[{player.current.source.title}]({player.current.source.webpage_url})",
            color=discord.Color.blue()
        )
        
        # Add duration if available
        if player.current.source.duration:
            minutes, seconds = divmod(player.current.source.duration, 60)
            hours, minutes = divmod(minutes, 60)
            
            duration = f"{int(minutes):02d}:{int(seconds):02d}"
            if hours > 0:
                duration = f"{int(hours):02d}:{duration}"
                
            embed.add_field(name="Duration", value=duration, inline=True)
            
        # Add requester if available
        if player.current.requester:
            embed.add_field(name="Requested by", value=player.current.requester.display_name, inline=True)
            
        # Add thumbnail if available
        if player.current.source.thumbnail:
            embed.set_thumbnail(url=player.current.source.thumbnail)
            
        # Show loop status
        embed.add_field(name="Loop", value="Enabled" if player.loop else "Disabled", inline=True)
        
        # Show volume
        embed.add_field(name="Volume", value=f"{int(player.volume * 100)}%", inline=True)
        
        # Add queue info
        if player.queue:
            embed.add_field(name="Up Next", value=f"{len(player.queue)} songs in queue", inline=True)
            
        await interaction.followup.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle bot disconnections and empty voice channels."""
        # If the bot was disconnected
        if member.id == self.bot.user.id and before.channel and not after.channel:
            # Clean up the player
            if member.guild.id in self.players:
                del self.players[member.guild.id]
        
        # If the bot is in a voice channel
        if member.guild.voice_client and member.guild.voice_client.channel:
            # Check if the channel is empty (except for the bot)
            channel = member.guild.voice_client.channel
            members = [m for m in channel.members if not m.bot]
            
            if not members:
                # Channel is empty, disconnect after a delay
                await asyncio.sleep(60)  # Wait 1 minute
                
                # Check again if still empty
                channel = member.guild.voice_client.channel if member.guild.voice_client else None
                if channel:
                    members = [m for m in channel.members if not m.bot]
                    if not members:
                        # Clean up the player
                        if member.guild.id in self.players:
                            await self.players[member.guild.id].stop()
                            del self.players[member.guild.id]

async def setup(bot):
    # Add yt_dlp to the requirements if not already installed
    try:
        import yt_dlp
    except ImportError:
        import pip
        pip.main(['install', 'yt-dlp'])
        
    # Check if ffmpeg is installed
    if not os.system('ffmpeg -version') == 0:
        print("WARNING: ffmpeg is not installed! Music features will not work.")
        print("Please install ffmpeg and make sure it's in your PATH.")
    
    await bot.add_cog(Music(bot)) 