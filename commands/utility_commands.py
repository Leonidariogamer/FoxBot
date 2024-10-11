import discord
from discord.ext import commands
from langdetect import detect
from utils import translate_text
from discord import Embed

# Cache to store deleted messages per channel
deleted_message_cache = {}

# Set up the bot commands
def setup(bot):
    # Remove the default help command to override it
    bot.remove_command('help')
    # Event listener for message deletion
    @bot.event
    async def on_message_delete(message):
        # Store the deleted message in the cache, keyed by the channel ID
        deleted_message_cache[message.channel.id] = message

    # Snipe Command to retrieve the last deleted message
    @bot.command(name='snipe')
    async def snipe(ctx):
        if ctx.channel.id in deleted_message_cache:
            message = deleted_message_cache[ctx.channel.id]
            embed = Embed(
                description=message.content,
                color=discord.Color.red(),
                timestamp=message.created_at
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("There's nothing to snipe.")

    # Translate Command
    @bot.command(name='translate')
    async def translate_command(ctx, *, text=None):
        if ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text_to_translate = replied_message.content
        elif text:
            text_to_translate = text
        else:
            messages = [message async for message in ctx.channel.history(limit=2)]
            text_to_translate = messages[1].content

        detected_language = detect(text_to_translate)
        translated_text = translate_text(text_to_translate)
        embed = Embed(title="Translation", description=f"**Original ({detected_language}):** {text_to_translate}\n\n**Translated (en):** {translated_text}", color=discord.Color.blue())
        await ctx.send(embed=embed)

    # Custom Help Command (overrides the default help command)
    @bot.command(name='help')
    async def custom_help(ctx):
        embed = Embed(
            title="Help - Command List",
            description="Here are the available commands.",
            color=discord.Color.blue()
        )

        # Moderation Commands
        embed.add_field(
            name="Moderation Commands",
            value="""
            `!warn <user> <reason>` - Warn a member.
            `!unwarn <user> <warning_id>` - Remove a warning by ID.
            `!kick <user> <reason>` - Kick a member from the server.
            `!ban <user> <reason>` - Ban a member from the server.
            `!unban <user>` - Unban a member.
            `!timeout <user> <duration>` - Timeout a member.
            `!untimeout <user>` - Remove a member's timeout.
            """,
            inline=False
        )

        # Utility Commands (excluding servers and invite)
        embed.add_field(
            name="Utility Commands",
            value="""
            `!snipe` - Retrieve the last deleted message.
            `!translate <text>` - Translate a message to English.
            `!help` - Display this help message.
	    `!server_settings` - Lets you either set a safe tag on e621 for all non NSFW channels and the ability to disable bot announcements
            `!steal` - Steal stickers and emojis from other servers
            """,
            inline=False
        )

        # Fun or Other Commands
        embed.add_field(
            name="NSFW Command",
            value="""
            `!e621 <tags>` - Fetch a random post from e621.net based on the specified tags(NO BLACKLIST).
            """,
            inline=False
        )

        # Send the help embed
        await ctx.send(embed=embed)

