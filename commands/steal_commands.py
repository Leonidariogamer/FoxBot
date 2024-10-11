# -*- coding: utf-8 -*-

import discord
from discord.ext import commands
from discord.ui import Button, View
import aiohttp
import re

# Helper function to add emoji to the server
async def add_emoji_to_server(guild, emoji_url, name):
    async with aiohttp.ClientSession() as session:
        async with session.get(emoji_url) as response:
            image_data = await response.read()
            new_emoji = await guild.create_custom_emoji(name=name, image=image_data)
            return new_emoji

# Helper function to add a sticker to the server
async def add_sticker_to_server(guild, sticker_url, name, sticker_format, bot_token):
    headers = {
        "Authorization": f"Bot {bot_token}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(sticker_url) as response:
            sticker_data = await response.read()

        # Prepare the multipart form-data payload for uploading the sticker
        form_data = aiohttp.FormData()
        form_data.add_field('name', name)
        form_data.add_field('tags', 'sticker')
        form_data.add_field('description', 'Copied Sticker')
        form_data.add_field('file', sticker_data, filename='sticker.png', content_type='image/png')

        upload_url = f"https://discord.com/api/v10/guilds/{guild.id}/stickers"

        async with session.post(upload_url, headers=headers, data=form_data) as resp:
            if resp.status == 201:
                sticker = await resp.json()
                return sticker
            else:
                error_text = await resp.text()
                raise Exception(f"Failed to upload sticker: {resp.status} - {error_text}")

# Steal command to add emoji or sticker
def setup(bot):
    @bot.command(name='steal')
    async def steal(ctx):
        target_message = ctx.message.reference
        if target_message:
            target_message = await ctx.channel.fetch_message(target_message.message_id)
        else:
            messages = [message async for message in ctx.channel.history(limit=2)]
            target_message = messages[1]

        emoji_url = None
        sticker_url = None
        name = None
        sticker_format = None

        if target_message.stickers:
            sticker = target_message.stickers[0]
            sticker_url = sticker.url
            name = sticker.name
            sticker_format = sticker.format
        else:
            custom_emoji_pattern = re.compile(r'<a?:(\w+):(\d+)>')
            match = custom_emoji_pattern.search(target_message.content)
            if match:
                emoji_name, emoji_id = match.groups()
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                name = emoji_name

        if not emoji_url and not sticker_url:
            await ctx.send("No custom emoji or sticker found to steal.")
            return

        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        view = View()
        accept_button = Button(label="Accept", style=discord.ButtonStyle.green)
        decline_button = Button(label="Decline", style=discord.ButtonStyle.red)

        async def accept_callback(interaction):
            await interaction.response.defer()

            if not interaction.user.guild_permissions.manage_emojis_and_stickers:
                await interaction.followup.send("You don't have permission to manage emojis/stickers.", ephemeral=True)
                return

            try:
                if emoji_url:
                    new_emoji = await add_emoji_to_server(ctx.guild, emoji_url, name)
                    await interaction.followup.send(f'Custom emoji :{name}: has been added to the server.')
                elif sticker_url:
                    new_sticker = await add_sticker_to_server(ctx.guild, sticker_url, name, sticker_format, bot.http.token)
                    await interaction.followup.send(f'Sticker {name} has been added to the server.')
            except Exception as e:
                await interaction.followup.send(f"Failed to add emoji/sticker: {e}")

        async def decline_callback(interaction):
            await interaction.response.send_message("Operation declined.", ephemeral=True)

        accept_button.callback = accept_callback
        decline_button.callback = decline_callback

        view.add_item(accept_button)
        view.add_item(decline_button)

        embed = discord.Embed(title="Steal Request", description="Do you want to add this custom emoji/sticker to the server?")
        await ctx.send(embed=embed, view=view)

