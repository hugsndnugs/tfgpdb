import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
from typing import Optional, Literal

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commands = {}
        self.load_commands()
        
    def load_commands(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            if os.path.exists('data/custom_commands.json'):
                with open('data/custom_commands.json', 'r') as f:
                    data = json.load(f)
                    
                    # Convert string keys to int (Discord IDs are stored as strings in JSON)
                    self.commands = {int(guild_id): guild_cmds for guild_id, guild_cmds in data.items()}
        except Exception as e:
            print(f"Error loading custom commands data: {e}")
            self.commands = {}
    
    def save_commands(self):
        if not os.path.exists('data'):
            os.makedirs('data')
            
        try:
            with open('data/custom_commands.json', 'w') as f:
                # Convert int keys to strings for JSON serialization
                data = {str(guild_id): guild_cmds for guild_id, guild_cmds in self.commands.items()}
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving custom commands data: {e}")
    
    @app_commands.command(name="addcmd", description="Add a custom command")
    @app_commands.describe(
        name="Name of the custom command (without prefix)",
        response="The response when the command is triggered",
        description="Description of what the command does"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def addcmd(self, interaction: discord.Interaction, name: str, response: str, description: str):
        # Validate command name (only allow letters, numbers, and underscores)
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            await interaction.response.send_message(
                "Command name can only contain letters, numbers, and underscores.", 
                ephemeral=True
            )
            return
            
        # Check for reserved commands
        if name in ['addcmd', 'editcmd', 'removecmd', 'listcmds']:
            await interaction.response.send_message(
                "This command name is reserved by the system and cannot be used.", 
                ephemeral=True
            )
            return
            
        # Check for existing bot commands
        for command in self.bot.tree.get_commands():
            if command.name == name:
                await interaction.response.send_message(
                    f"A slash command with the name `{name}` already exists.", 
                    ephemeral=True
                )
                return
        
        guild_id = interaction.guild.id
        
        # Initialize guild commands if not exists
        if guild_id not in self.commands:
            self.commands[guild_id] = {}
            
        # Check if command already exists for this guild
        if name in self.commands[guild_id]:
            await interaction.response.send_message(
                f"Command `{name}` already exists. Use `/editcmd` to modify it.", 
                ephemeral=True
            )
            return
            
        # Add the command
        self.commands[guild_id][name] = {
            'response': response,
            'description': description,
            'creator_id': interaction.user.id,
            'created_at': interaction.created_at.isoformat()
        }
        
        self.save_commands()
        
        # Register the command with Discord
        @app_commands.command(name=name, description=description)
        async def custom_command(cmd_interaction: discord.Interaction):
            await cmd_interaction.response.send_message(response)
            
        # Add the command to the bot
        self.bot.tree.add_command(custom_command, guild=discord.Object(id=guild_id))
        
        # Sync commands with Discord
        await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        
        await interaction.response.send_message(
            f"Custom command `/{name}` has been added successfully.", 
            ephemeral=True
        )
    
    @app_commands.command(name="editcmd", description="Edit an existing custom command")
    @app_commands.describe(
        name="Name of the custom command to edit",
        response="The new response for the command",
        description="New description of what the command does"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def editcmd(self, interaction: discord.Interaction, name: str, response: Optional[str] = None, description: Optional[str] = None):
        guild_id = interaction.guild.id
        
        # Check if guild has any commands
        if guild_id not in self.commands:
            await interaction.response.send_message(
                "This server doesn't have any custom commands yet.", 
                ephemeral=True
            )
            return
            
        # Check if command exists
        if name not in self.commands[guild_id]:
            await interaction.response.send_message(
                f"Command `{name}` doesn't exist. Use `/addcmd` to create it.", 
                ephemeral=True
            )
            return
            
        # Get current values
        current = self.commands[guild_id][name]
        
        # Update values
        if response is not None:
            current['response'] = response
        if description is not None:
            current['description'] = description
            
        # Update metadata
        current['last_edited_by'] = interaction.user.id
        current['last_edited_at'] = interaction.created_at.isoformat()
        
        self.save_commands()
        
        # Update the command in Discord
        # Remove the old command
        for command in self.bot.tree.get_commands(guild=discord.Object(id=guild_id)):
            if command.name == name:
                self.bot.tree.remove_command(command.name, guild=discord.Object(id=guild_id))
                
        # Add the updated command
        @app_commands.command(name=name, description=current['description'])
        async def custom_command(cmd_interaction: discord.Interaction):
            await cmd_interaction.response.send_message(current['response'])
            
        # Add the command to the bot
        self.bot.tree.add_command(custom_command, guild=discord.Object(id=guild_id))
        
        # Sync commands with Discord
        await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        
        await interaction.response.send_message(
            f"Custom command `/{name}` has been updated successfully.", 
            ephemeral=True
        )
    
    @app_commands.command(name="removecmd", description="Remove a custom command")
    @app_commands.describe(
        name="Name of the custom command to remove"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def removecmd(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild.id
        
        # Check if guild has any commands
        if guild_id not in self.commands:
            await interaction.response.send_message(
                "This server doesn't have any custom commands.", 
                ephemeral=True
            )
            return
            
        # Check if command exists
        if name not in self.commands[guild_id]:
            await interaction.response.send_message(
                f"Command `{name}` doesn't exist.", 
                ephemeral=True
            )
            return
            
        # Remove the command
        del self.commands[guild_id][name]
        
        # Clean up if guild has no more commands
        if not self.commands[guild_id]:
            del self.commands[guild_id]
            
        self.save_commands()
        
        # Remove the command from Discord
        for command in self.bot.tree.get_commands(guild=discord.Object(id=guild_id)):
            if command.name == name:
                self.bot.tree.remove_command(command.name, guild=discord.Object(id=guild_id))
                
        # Sync commands with Discord
        await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        
        await interaction.response.send_message(
            f"Custom command `/{name}` has been removed successfully.", 
            ephemeral=True
        )
    
    @app_commands.command(name="listcmds", description="List all custom commands in this server")
    @app_commands.describe(
        format="Output format (default: embed)"
    )
    async def listcmds(self, interaction: discord.Interaction, format: Optional[Literal["embed", "text"]] = "embed"):
        guild_id = interaction.guild.id
        
        # Check if guild has any commands
        if guild_id not in self.commands or not self.commands[guild_id]:
            await interaction.response.send_message(
                "This server doesn't have any custom commands yet.", 
                ephemeral=True
            )
            return
            
        # Get sorted list of commands
        cmd_list = sorted(self.commands[guild_id].items())
        
        if format == "embed":
            # Create embed
            embed = discord.Embed(
                title="Custom Commands",
                description=f"This server has {len(cmd_list)} custom commands.",
                color=discord.Color.blue()
            )
            
            # Add commands to embed
            for name, data in cmd_list:
                embed.add_field(
                    name=f"/{name}", 
                    value=f"Description: {data['description']}\nResponse: {data['response'][:100]}{'...' if len(data['response']) > 100 else ''}", 
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
        else:
            # Text format
            lines = [f"**Custom Commands ({len(cmd_list)})**"]
            
            for name, data in cmd_list:
                lines.append(f"**/{name}** - {data['description']}")
                
            await interaction.response.send_message("\n".join(lines))
    
    @app_commands.command(name="cmdinfo", description="Get detailed information about a custom command")
    @app_commands.describe(
        name="Name of the custom command"
    )
    async def cmdinfo(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild.id
        
        # Check if guild has any commands
        if guild_id not in self.commands:
            await interaction.response.send_message(
                "This server doesn't have any custom commands.", 
                ephemeral=True
            )
            return
            
        # Check if command exists
        if name not in self.commands[guild_id]:
            await interaction.response.send_message(
                f"Command `{name}` doesn't exist.", 
                ephemeral=True
            )
            return
            
        # Get command data
        data = self.commands[guild_id][name]
        
        # Create embed
        embed = discord.Embed(
            title=f"Command: /{name}",
            description=data['description'],
            color=discord.Color.blue()
        )
        
        # Add creator info if available
        creator_id = data.get('creator_id')
        if creator_id:
            try:
                creator = await self.bot.fetch_user(creator_id)
                embed.add_field(name="Created by", value=f"{creator.name} ({creator.id})", inline=True)
            except:
                embed.add_field(name="Created by", value=f"Unknown User ({creator_id})", inline=True)
                
        # Add creation date
        if 'created_at' in data:
            embed.add_field(name="Created at", value=data['created_at'], inline=True)
            
        # Add last editor if available
        editor_id = data.get('last_edited_by')
        if editor_id:
            try:
                editor = await self.bot.fetch_user(editor_id)
                embed.add_field(name="Last edited by", value=f"{editor.name} ({editor.id})", inline=True)
            except:
                embed.add_field(name="Last edited by", value=f"Unknown User ({editor_id})", inline=True)
                
        # Add last edit date
        if 'last_edited_at' in data:
            embed.add_field(name="Last edited at", value=data['last_edited_at'], inline=True)
            
        # Add response
        embed.add_field(name="Response", value=data['response'], inline=False)
        
        await interaction.response.send_message(embed=embed)

    async def sync_commands(self):
        """Sync all custom commands with Discord after bot startup"""
        await self.bot.wait_until_ready()
        
        for guild_id, guild_cmds in self.commands.items():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            for name, data in guild_cmds.items():
                # Create command
                @app_commands.command(name=name, description=data['description'])
                async def custom_command(interaction: discord.Interaction):
                    cmd_name = interaction.command.name
                    guild_id = interaction.guild.id
                    
                    if guild_id in self.commands and cmd_name in self.commands[guild_id]:
                        await interaction.response.send_message(self.commands[guild_id][cmd_name]['response'])
                
                # Add the command to the bot
                try:
                    self.bot.tree.add_command(custom_command, guild=discord.Object(id=guild_id))
                except Exception as e:
                    print(f"Error adding command {name}: {e}")
                    
            # Sync commands with Discord
            try:
                await self.bot.tree.sync(guild=discord.Object(id=guild_id))
            except Exception as e:
                print(f"Error syncing commands for guild {guild_id}: {e}")
                
    async def cog_load(self):
        """Tasks to run when the cog is loaded"""
        self.bot.loop.create_task(self.sync_commands())

async def setup(bot):
    await bot.add_cog(CustomCommands(bot)) 