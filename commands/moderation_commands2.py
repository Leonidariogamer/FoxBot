import discord
from discord.ext import commands
from discord import Embed
from database import connect_db

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Warn a member
    @commands.command(name='warn')
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        conn = connect_db()
        cursor = conn.cursor()

        # Insert warning into the database
        cursor.execute("INSERT INTO warnings (user_id, guild_id, reason) VALUES (?, ?, ?)", (member.id, ctx.guild.id, reason))
        conn.commit()
        conn.close()

        embed = Embed(
            title="Warning Issued",
            description=f"{member.mention} has been warned for: **{reason}**",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    # Remove the last warning for a member (unwarn)
    @commands.command(name='unwarn')
    @commands.has_permissions(kick_members=True)
    async def unwarn(self, ctx, member: discord.Member):
        conn = connect_db()
        cursor = conn.cursor()

        # Delete the most recent warning for the user
        cursor.execute("DELETE FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY id DESC LIMIT 1", (member.id, ctx.guild.id))
        conn.commit()
        conn.close()

        embed = Embed(
            title="Warning Removed",
            description=f"The last warning for {member.mention} has been removed.",
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
        cursor.execute("SELECT reason FROM warnings WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        warnings = cursor.fetchall()
        conn.close()

        if warnings:
            warning_list = "\n".join([f"- {warning[0]}" for warning in warnings])
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

    # Kick a member
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.kick(reason=reason)
        embed = Embed(
            title="Member Kicked",
            description=f"{member.mention} has been kicked for: **{reason}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # Ban a member
    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.ban(reason=reason)
        embed = Embed(
            title="Member Banned",
            description=f"{member.mention} has been banned for: **{reason}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # Unban a member
    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member_name: str):
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member_name.split('#')

        for ban_entry in banned_users:
            user = ban_entry.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                embed = Embed(
                    title="Member Unbanned",
                    description=f"{user.mention} has been unbanned.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return

        await ctx.send("User not found.")

# Function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ModerationCommands(bot))