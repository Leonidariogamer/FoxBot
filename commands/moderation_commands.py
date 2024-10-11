import discord
from discord.ext import commands
from discord import Embed
from database import connect_db
import asyncio

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Warn a member
    @commands.command(name='warn')
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        conn = connect_db()
        cursor = conn.cursor()

        # Insert warning into the database and retrieve the unique ID
        cursor.execute("INSERT INTO warnings (user_id, guild_id, reason) VALUES (?, ?, ?)", (member.id, ctx.guild.id, reason))
        warning_id = cursor.lastrowid  # Get the ID of the inserted warning
        conn.commit()
        conn.close()

        embed = Embed(
            title="Warning Issued",
            description=f"{member.mention} has been warned for: **{reason}**\nWarning ID: `{warning_id}`",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    # Remove a specific warning by ID (unwarn)
    @commands.command(name='unwarn')
    @commands.has_permissions(kick_members=True)
    async def unwarn(self, ctx, member: discord.Member, warning_id: int):
        conn = connect_db()
        cursor = conn.cursor()

        # Delete the specific warning by ID
        cursor.execute("DELETE FROM warnings WHERE id = ? AND user_id = ? AND guild_id = ?", (warning_id, member.id, ctx.guild.id))
        conn.commit()
        conn.close()

        embed = Embed(
            title="Warning Removed",
            description=f"The warning with ID `{warning_id}` for {member.mention} has been removed.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Check warnings for a member
    @commands.command(name='warnings')
    async def warnings(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author  # Default to the person issuing the command

        conn = connect_db()
        cursor = conn.cursor()

        # Fetch warnings from the database
        cursor.execute("SELECT id, reason, timestamp FROM warnings WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        warnings = cursor.fetchall()
        conn.close()

        if warnings:
            warning_list = "\n".join([f"ID: {warning[0]}, Reason: {warning[1]}, Date: {warning[2]}" for warning in warnings])
            embed = Embed(
                title=f"{member.display_name}'s Warnings",
                description=warning_list,
                color=discord.Color.red()
            )
        else:
            embed = Embed(
                title=f"{member.display_name}'s Warnings",
                description="No warnings found.",
                color=discord.Color.green()
            )
        
        await ctx.send(embed=embed)

    # Timeout a member (mute for a specific duration)
    @commands.command(name='timeout')
    @commands.has_permissions(moderate_members=True)  # This permission is needed for timeout
    async def timeout(self, ctx, member: discord.Member, duration: int, *, reason="No reason provided"):
        # Timeout the member for the specified duration (in minutes)
        await member.timeout_for(duration=discord.utils.utcnow() + discord.utils.timedelta(minutes=duration), reason=reason)

        embed = Embed(
            title="Member Timed Out",
            description=f"{member.mention} has been timed out for {duration} minutes for: **{reason}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # Remove timeout from a member
    @commands.command(name='untimeout')
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        # Remove the timeout (mute) from the member
        await member.edit(timed_out_until=None)

        embed = Embed(
            title="Member Untimed Out",
            description=f"{member.mention} is no longer in timeout.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

# Function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ModerationCommands(bot))