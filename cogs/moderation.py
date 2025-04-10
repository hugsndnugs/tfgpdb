import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for kicking")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't kick someone with a higher or equal role!", ephemeral=True)
            return
        
        await member.kick(reason=reason)
        await interaction.response.send_message(f'Kicked {member.mention} for {reason}')

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for banning")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't ban someone with a higher or equal role!", ephemeral=True)
            return
        
        await member.ban(reason=reason)
        await interaction.response.send_message(f'Banned {member.mention} for {reason}')

    @app_commands.command(name="unban", description="Unban a member from the server")
    @app_commands.describe(user_id="The user ID to unban")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(f'Unbanned {user.mention}')
        except discord.NotFound:
            await interaction.response.send_message(f'User with ID {user_id} not found.', ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message(f'Failed to unban user with ID {user_id}.', ephemeral=True)

    @app_commands.command(name="clear", description="Clear a specified number of messages")
    @app_commands.describe(amount="The number of messages to clear (max 100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount <= 0 or amount > 100:
            await interaction.response.send_message("Please provide a number between 1 and 100.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        # Delete messages
        deleted = await interaction.channel.purge(limit=amount)
        
        # Send confirmation
        await interaction.followup.send(f'Cleared {len(deleted)} messages!', ephemeral=True)

    @app_commands.command(name="mute", description="Mute a member")
    @app_commands.describe(member="The member to mute", reason="Reason for muting")
    @app_commands.default_permissions(manage_roles=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        
        if not muted_role:
            # Defer the response as creating a role might take some time
            await interaction.response.defer(ephemeral=True)
            
            # Create the muted role
            muted_role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(muted_role, speak=False, send_messages=False)
                
            # Add the role to the member
            await member.add_roles(muted_role, reason=reason)
            await interaction.followup.send(f'Created Muted role and muted {member.mention} for {reason}')
        else:
            # Add the role to the member
            await member.add_roles(muted_role, reason=reason)
            await interaction.response.send_message(f'Muted {member.mention} for {reason}')

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="The member to unmute")
    @app_commands.default_permissions(manage_roles=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if muted_role not in member.roles:
            await interaction.response.send_message(f'{member.mention} is not muted.', ephemeral=True)
            return
            
        await member.remove_roles(muted_role)
        await interaction.response.send_message(f'Unmuted {member.mention}')

async def setup(bot):
    await bot.add_cog(Moderation(bot)) 