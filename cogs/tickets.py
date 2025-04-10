import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime
from typing import Optional

class TicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket:create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Get ticket manager
        ticket_manager = self.bot.get_cog("Tickets")
        if not ticket_manager:
            await interaction.followup.send("Ticket system is currently unavailable.", ephemeral=True)
            return
            
        await ticket_manager.create_ticket(interaction)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.load_config()
        
        # Register persistent view
        self.bot.add_view(TicketView(bot))
        
    def load_config(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            if os.path.exists('data/tickets.json'):
                with open('data/tickets.json', 'r') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"Error loading tickets config: {e}")
            self.config = {}
    
    def save_config(self):
        if not os.path.exists('data'):
            os.makedirs('data')
            
        try:
            with open('data/tickets.json', 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving tickets config: {e}")
    
    @app_commands.command(name="ticketpanel", description="Create a ticket panel for users to open support tickets")
    @app_commands.describe(
        channel="Channel to send the ticket panel to",
        title="Title for the ticket panel",
        description="Description for the ticket panel"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticketpanel(self, interaction: discord.Interaction, channel: discord.TextChannel, 
                         title: str = "Support Tickets", 
                         description: str = "Click the button below to create a support ticket."):
        await interaction.response.defer(ephemeral=True)
        
        # Create the embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Create the view with the button
        view = TicketView(self.bot)
        
        # Send the panel
        await channel.send(embed=embed, view=view)
        
        # Update guild config
        guild_id = str(interaction.guild.id)
        if guild_id not in self.config:
            self.config[guild_id] = {
                'ticket_count': 0,
                'ticket_category': None,
                'support_roles': [],
                'ticket_log': None,
                'ticket_close_message': "This ticket has been closed and will be deleted in 10 seconds.",
                'ticket_welcome_message': "Support will be with you shortly. Please describe your issue in detail."
            }
            
        self.save_config()
        
        await interaction.followup.send("Ticket panel has been created successfully!", ephemeral=True)
    
    @app_commands.command(name="ticketsetup", description="Configure the ticket system settings")
    @app_commands.describe(
        category="Category to create tickets in",
        log_channel="Channel to log ticket actions"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticketsetup(self, interaction: discord.Interaction, category: Optional[discord.CategoryChannel] = None, 
                         log_channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True)
        
        # Initialize guild config if not exists
        guild_id = str(interaction.guild.id)
        if guild_id not in self.config:
            self.config[guild_id] = {
                'ticket_count': 0,
                'ticket_category': None,
                'support_roles': [],
                'ticket_log': None,
                'ticket_close_message': "This ticket has been closed and will be deleted in 10 seconds.",
                'ticket_welcome_message': "Support will be with you shortly. Please describe your issue in detail."
            }
        
        # Update the config with provided values
        if category:
            self.config[guild_id]['ticket_category'] = category.id
            
        if log_channel:
            self.config[guild_id]['ticket_log'] = log_channel.id
            
        self.save_config()
        
        # Build response message
        response = ["Ticket system configuration updated:"]
        
        if category:
            response.append(f"• Ticket Category: {category.name}")
            
        if log_channel:
            response.append(f"• Log Channel: {log_channel.mention}")
            
        if not any([category, log_channel]):
            response.append("No changes were made. Use the parameters to update specific settings.")
            
        await interaction.followup.send("\n".join(response), ephemeral=True)
    
    @app_commands.command(name="addsupportrole", description="Add a role to the ticket support team")
    @app_commands.describe(
        role="Role to add as support staff"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def addsupportrole(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        
        # Initialize guild config if not exists
        guild_id = str(interaction.guild.id)
        if guild_id not in self.config:
            self.config[guild_id] = {
                'ticket_count': 0,
                'ticket_category': None,
                'support_roles': [],
                'ticket_log': None,
                'ticket_close_message': "This ticket has been closed and will be deleted in 10 seconds.",
                'ticket_welcome_message': "Support will be with you shortly. Please describe your issue in detail."
            }
        
        # Check if role is already in support roles
        if role.id in self.config[guild_id]['support_roles']:
            await interaction.followup.send(f"{role.mention} is already a support role.", ephemeral=True)
            return
            
        # Add the role to support roles
        self.config[guild_id]['support_roles'].append(role.id)
        self.save_config()
        
        await interaction.followup.send(f"Added {role.mention} to the support team.", ephemeral=True)
    
    @app_commands.command(name="removesupportrole", description="Remove a role from the ticket support team")
    @app_commands.describe(
        role="Role to remove from support staff"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def removesupportrole(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        
        # Initialize guild config if not exists
        guild_id = str(interaction.guild.id)
        if guild_id not in self.config:
            self.config[guild_id] = {
                'ticket_count': 0,
                'ticket_category': None,
                'support_roles': [],
                'ticket_log': None,
                'ticket_close_message': "This ticket has been closed and will be deleted in 10 seconds.",
                'ticket_welcome_message': "Support will be with you shortly. Please describe your issue in detail."
            }
        
        # Check if role is in support roles
        if role.id not in self.config[guild_id]['support_roles']:
            await interaction.followup.send(f"{role.mention} is not a support role.", ephemeral=True)
            return
            
        # Remove the role from support roles
        self.config[guild_id]['support_roles'].remove(role.id)
        self.save_config()
        
        await interaction.followup.send(f"Removed {role.mention} from the support team.", ephemeral=True)
    
    async def create_ticket(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        
        # Check if guild is configured
        if guild_id not in self.config:
            await interaction.followup.send("Ticket system is not configured for this server.", ephemeral=True)
            return
            
        # Check for category
        category_id = self.config[guild_id].get('ticket_category')
        category = None
        
        if category_id:
            category = interaction.guild.get_channel(category_id)
            
        if not category:
            # Try to find a category named "Tickets"
            category = discord.utils.get(interaction.guild.categories, name="Tickets")
            
            # If still not found, create one
            if not category:
                try:
                    category = await interaction.guild.create_category("Tickets")
                    self.config[guild_id]['ticket_category'] = category.id
                    self.save_config()
                except:
                    await interaction.followup.send("Failed to create ticket category. Please set one with `/ticketsetup`.", ephemeral=True)
                    return
        
        # Check for existing ticket
        for channel in category.channels:
            if channel.topic and f"Ticket for {interaction.user.id}" in channel.topic:
                await interaction.followup.send(f"You already have an open ticket: {channel.mention}", ephemeral=True)
                return
            
        # Increment ticket count
        self.config[guild_id]['ticket_count'] += 1
        ticket_num = self.config[guild_id]['ticket_count']
        self.save_config()
        
        # Create permissions for the channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        # Add permissions for support roles
        for role_id in self.config[guild_id].get('support_roles', []):
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True)
        
        # Create the ticket channel
        ticket_channel = await category.create_text_channel(
            name=f"ticket-{ticket_num}",
            topic=f"Ticket for {interaction.user.id}",
            overwrites=overwrites
        )
        
        # Create control buttons
        class TicketControls(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id=f"ticket:close:{ticket_channel.id}")
            async def close_ticket(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_message("Closing ticket...")
                await asyncio.sleep(3)
                await ticket_channel.send("This ticket will be deleted in 10 seconds.")
                await asyncio.sleep(10)
                await ticket_channel.delete()
        
        # Send the welcome message
        welcome_message = self.config[guild_id].get('ticket_welcome_message', "Support will be with you shortly. Please describe your issue in detail.")
        
        welcome_embed = discord.Embed(
            title=f"Ticket #{ticket_num}",
            description=welcome_message,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        welcome_embed.add_field(name="User", value=interaction.user.mention)
        
        await ticket_channel.send(f"{interaction.user.mention}", embed=welcome_embed, view=TicketControls())
        
        # Log if log channel is set
        log_channel_id = self.config[guild_id].get('ticket_log')
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                # Create log embed
                log_embed = discord.Embed(
                    title=f"Ticket Created: #{ticket_num}",
                    description=f"Ticket created by {interaction.user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                await log_channel.send(embed=log_embed)
        
        await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot)) 