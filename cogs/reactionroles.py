import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import Optional

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles = {}
        self.load_reaction_roles()
        
    def load_reaction_roles(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            if os.path.exists('data/reaction_roles.json'):
                with open('data/reaction_roles.json', 'r') as f:
                    data = json.load(f)
                    
                    # Convert string keys to int (Discord IDs are stored as strings in JSON)
                    self.reaction_roles = {int(k): {int(msg_id): {emoji: int(role_id) for emoji, role_id in roles.items()} 
                                         for msg_id, roles in v.items()} 
                                for k, v in data.items()}
        except Exception as e:
            print(f"Error loading reaction roles data: {e}")
            self.reaction_roles = {}
    
    def save_reaction_roles(self):
        if not os.path.exists('data'):
            os.makedirs('data')
            
        try:
            with open('data/reaction_roles.json', 'w') as f:
                # Convert int keys to strings for JSON serialization
                data = {str(k): {str(msg_id): {emoji: str(role_id) for emoji, role_id in roles.items()} 
                               for msg_id, roles in v.items()} 
                      for k, v in self.reaction_roles.items()}
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving reaction roles data: {e}")
    
    @app_commands.command(name="reactionrole", description="Create a reaction role message")
    @app_commands.describe(
        title="Title of the reaction role message",
        description="Description for the reaction role message (optional)"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def reactionrole(self, interaction: discord.Interaction, title: str, description: Optional[str] = None):
        await interaction.response.send_message(
            "Creating reaction role message. Please use `/addrole` to add roles to it.", 
            ephemeral=True
        )
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=description or "React to get roles!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="React to get roles | Managed by The Final General Purpose Discord Bot")
        
        # Send the message
        message = await interaction.channel.send(embed=embed)
        
        # Initialize in our tracking dict
        guild_id = interaction.guild.id
        if guild_id not in self.reaction_roles:
            self.reaction_roles[guild_id] = {}
            
        self.reaction_roles[guild_id][message.id] = {}
        self.save_reaction_roles()
    
    @app_commands.command(name="addrole", description="Add a role to a reaction role message")
    @app_commands.describe(
        message_id="ID of the reaction role message",
        role="Role to add",
        emoji="Emoji to use for this role",
        description="Description for this role (optional)"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def addrole(self, interaction: discord.Interaction, message_id: str, role: discord.Role, emoji: str, description: Optional[str] = None):
        try:
            msg_id = int(message_id)
            guild_id = interaction.guild.id
            
            # Check if the reaction role message exists
            if guild_id not in self.reaction_roles or msg_id not in self.reaction_roles[guild_id]:
                await interaction.response.send_message(
                    "Reaction role message not found. Make sure you've created one with `/reactionrole` first.", 
                    ephemeral=True
                )
                return
                
            # Check if the role is higher than the bot's highest role
            if role.position >= interaction.guild.me.top_role.position:
                await interaction.response.send_message(
                    "I cannot assign this role as it's higher than or equal to my highest role.", 
                    ephemeral=True
                )
                return
            
            # Get the message
            try:
                channel = interaction.channel
                message = await channel.fetch_message(msg_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    "Message not found in this channel. Make sure you're using this command in the same channel as the reaction role message.", 
                    ephemeral=True
                )
                return
            
            # Update the embed
            embed = message.embeds[0]
            current_description = embed.description
            
            # Add the new role to the description
            role_text = f"{emoji} - {role.mention}"
            if description:
                role_text += f" - {description}"
                
            # Update the description
            if current_description and current_description != "React to get roles!":
                new_description = f"{current_description}\n{role_text}"
            else:
                new_description = role_text
                
            embed.description = new_description
            await message.edit(embed=embed)
            
            # Add the reaction to the message
            await message.add_reaction(emoji)
            
            # Save the role in our system
            self.reaction_roles[guild_id][msg_id][emoji] = role.id
            self.save_reaction_roles()
            
            await interaction.response.send_message(
                f"Added {role.name} with {emoji} to the reaction role message.", 
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message("Invalid message ID. Please provide a valid number.", ephemeral=True)
    
    @app_commands.command(name="removerole", description="Remove a role from a reaction role message")
    @app_commands.describe(
        message_id="ID of the reaction role message",
        emoji="Emoji of the role to remove"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def removerole(self, interaction: discord.Interaction, message_id: str, emoji: str):
        try:
            msg_id = int(message_id)
            guild_id = interaction.guild.id
            
            # Check if the reaction role message exists
            if guild_id not in self.reaction_roles or msg_id not in self.reaction_roles[guild_id]:
                await interaction.response.send_message(
                    "Reaction role message not found.", 
                    ephemeral=True
                )
                return
                
            # Check if the emoji exists in the reaction roles
            if emoji not in self.reaction_roles[guild_id][msg_id]:
                await interaction.response.send_message(
                    "This emoji is not associated with any role in this message.", 
                    ephemeral=True
                )
                return
            
            # Get the message
            try:
                channel = interaction.channel
                message = await channel.fetch_message(msg_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    "Message not found in this channel.", 
                    ephemeral=True
                )
                return
            
            # Get the role ID and name for confirmation
            role_id = self.reaction_roles[guild_id][msg_id][emoji]
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else "Unknown Role"
            
            # Remove the reaction from the message
            for reaction in message.reactions:
                if str(reaction.emoji) == emoji:
                    await reaction.clear()
                    break
            
            # Update the embed to remove the role
            embed = message.embeds[0]
            description_lines = embed.description.split('\n')
            new_description_lines = []
            
            for line in description_lines:
                if not line.startswith(emoji):
                    new_description_lines.append(line)
            
            new_description = '\n'.join(new_description_lines)
            if not new_description:
                new_description = "React to get roles!"
                
            embed.description = new_description
            await message.edit(embed=embed)
            
            # Remove the role from our system
            del self.reaction_roles[guild_id][msg_id][emoji]
            self.save_reaction_roles()
            
            await interaction.response.send_message(
                f"Removed {role_name} with {emoji} from the reaction role message.", 
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message("Invalid message ID. Please provide a valid number.", ephemeral=True)
    
    @app_commands.command(name="listroles", description="List all reaction roles for a message")
    @app_commands.describe(
        message_id="ID of the reaction role message"
    )
    async def listroles(self, interaction: discord.Interaction, message_id: str):
        try:
            msg_id = int(message_id)
            guild_id = interaction.guild.id
            
            # Check if the reaction role message exists
            if guild_id not in self.reaction_roles or msg_id not in self.reaction_roles[guild_id]:
                await interaction.response.send_message(
                    "Reaction role message not found.", 
                    ephemeral=True
                )
                return
            
            # Get all the roles
            roles_data = self.reaction_roles[guild_id][msg_id]
            if not roles_data:
                await interaction.response.send_message(
                    "No roles have been added to this message yet.", 
                    ephemeral=True
                )
                return
            
            # Create an embed to display the roles
            embed = discord.Embed(
                title="Reaction Roles",
                description=f"Roles for message ID: {msg_id}",
                color=discord.Color.blue()
            )
            
            for emoji, role_id in roles_data.items():
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else "Unknown Role (deleted)"
                embed.add_field(name=f"{emoji}", value=role_name, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("Invalid message ID. Please provide a valid number.", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
            
        guild_id = payload.guild_id
        message_id = payload.message_id
        emoji = str(payload.emoji)
        
        # Check if this is a reaction role message
        if (guild_id in self.reaction_roles and 
            message_id in self.reaction_roles[guild_id] and 
            emoji in self.reaction_roles[guild_id][message_id]):
                
            # Get the guild and member
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
                
            member = guild.get_member(payload.user_id)
            if not member:
                try:
                    member = await guild.fetch_member(payload.user_id)
                except discord.errors.NotFound:
                    return
            
            # Get the role
            role_id = self.reaction_roles[guild_id][message_id][emoji]
            role = guild.get_role(role_id)
            
            if not role:
                # Role was deleted, clean up
                del self.reaction_roles[guild_id][message_id][emoji]
                self.save_reaction_roles()
                return
            
            # Add the role to the member
            try:
                await member.add_roles(role, reason="Reaction Role")
            except discord.Forbidden:
                # Bot doesn't have permission
                print(f"Cannot add role {role.name} to {member.name} - missing permissions")
            except Exception as e:
                print(f"Error adding role: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
            
        guild_id = payload.guild_id
        message_id = payload.message_id
        emoji = str(payload.emoji)
        
        # Check if this is a reaction role message
        if (guild_id in self.reaction_roles and 
            message_id in self.reaction_roles[guild_id] and 
            emoji in self.reaction_roles[guild_id][message_id]):
                
            # Get the guild and member
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
                
            member = guild.get_member(payload.user_id)
            if not member:
                try:
                    member = await guild.fetch_member(payload.user_id)
                except discord.errors.NotFound:
                    return
            
            # Get the role
            role_id = self.reaction_roles[guild_id][message_id][emoji]
            role = guild.get_role(role_id)
            
            if not role:
                # Role was deleted, clean up
                del self.reaction_roles[guild_id][message_id][emoji]
                self.save_reaction_roles()
                return
            
            # Remove the role from the member
            try:
                await member.remove_roles(role, reason="Reaction Role")
            except discord.Forbidden:
                # Bot doesn't have permission
                print(f"Cannot remove role {role.name} from {member.name} - missing permissions")
            except Exception as e:
                print(f"Error removing role: {e}")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot)) 