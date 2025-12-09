import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import discord
import requests
from deep_translator import GoogleTranslator
from discord import Embed
from discord.ext import commands, tasks
from langdetect import detect

# ====== File-based storage helpers ======
GUILD_DATA_DIR = Path("guild_data")
GUILD_DATA_DIR.mkdir(exist_ok=True)


def _guild_dir(guild_id: int) -> Path:
    path = GUILD_DATA_DIR / str(guild_id)
    path.mkdir(exist_ok=True)
    return path


def _load_json(path: Path, default):
    if path.exists():
        with path.open("r", encoding="utf-8") as fp:
            try:
                return json.load(fp)
            except json.JSONDecodeError:
                return default
    return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)


def get_guild_settings(guild_id: int) -> Dict[str, bool]:
    settings_path = _guild_dir(guild_id) / "settings.json"
    default_settings = {"e621_safe_mode": False, "broadcast_enabled": True}
    return _load_json(settings_path, default_settings)


def save_guild_settings(guild_id: int, settings: Dict[str, bool]) -> None:
    settings_path = _guild_dir(guild_id) / "settings.json"
    _save_json(settings_path, settings)


def _warnings_path(guild_id: int) -> Path:
    return _guild_dir(guild_id) / "warnings.json"


def _load_warnings(guild_id: int) -> List[Dict]:
    return _load_json(_warnings_path(guild_id), [])


def _save_warnings(guild_id: int, warnings: List[Dict]) -> None:
    _save_json(_warnings_path(guild_id), warnings)


def add_warning(guild_id: int, user_id: int, reason: str) -> int:
    warnings = _load_warnings(guild_id)
    next_id = 1 if not warnings else max(w["id"] for w in warnings) + 1
    warnings.append(
        {
            "id": next_id,
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    _save_warnings(guild_id, warnings)
    return next_id


def remove_warning(guild_id: int, user_id: int, warning_id: int) -> bool:
    warnings = _load_warnings(guild_id)
    new_warnings = [w for w in warnings if not (w["id"] == warning_id and w["user_id"] == user_id)]
    _save_warnings(guild_id, new_warnings)
    return len(new_warnings) != len(warnings)


def remove_last_warning(guild_id: int, user_id: int) -> bool:
    warnings = _load_warnings(guild_id)
    filtered = [w for w in warnings if w["user_id"] == user_id]
    if not filtered:
        return False
    last_id = max(w["id"] for w in filtered)
    return remove_warning(guild_id, user_id, last_id)


def list_warnings(guild_id: int, user_id: int) -> List[Dict]:
    warnings = _load_warnings(guild_id)
    return [w for w in warnings if w["user_id"] == user_id]


# ====== External helpers ======
def fetch_e621_post(tags) -> Optional[dict]:
    tags = " ".join(tags)
    url = f"https://e621.net/posts.json?tags={tags}&limit=100"
    headers = {"User-Agent": "FoxBot/1.0 (example@example.com)"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("posts"):
            return data["posts"][0]
    return None


def translate_text(text: str, target_language: str = "en") -> str:
    translator = GoogleTranslator(source="auto", target=target_language)
    return translator.translate(text)


# ====== Discord bot setup ======
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Cache to store deleted messages per channel for snipe
_deleted_message_cache: Dict[int, discord.Message] = {}


class DeleteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Delete", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()


class DeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeleteButton())


@tasks.loop(minutes=2)
async def update_status():
    server_count = len(bot.guilds)
    status_message = f"Helping in {server_count} servers"
    stream_activity = discord.Streaming(name=status_message, url="https://www.youtube.com/watch?v=At8v_Yc044Y")
    await bot.change_presence(activity=stream_activity)


async def connect_to_voice_channel():
    guild = discord.utils.get(bot.guilds)
    if guild:
        voice_channel_id = os.getenv("VOICE_CHANNEL_ID")
        if voice_channel_id:
            channel = discord.utils.get(guild.voice_channels, id=int(voice_channel_id))
            if channel:
                await channel.connect()


@bot.event
async def on_message_delete(message: discord.Message):
    _deleted_message_cache[message.channel.id] = message


@bot.event
async def on_ready():
    print(f"Bot is ready! Serving {len(bot.guilds)} servers.")
    if not update_status.is_running():
        update_status.start()
    await connect_to_voice_channel()
    await bot.tree.sync()


# ====== Commands ======
@bot.hybrid_command(name="e621", description="Fetch a random post from e621 based on tags.")
async def e621(ctx: commands.Context, *, tags: Optional[str] = None):
    if not tags:
        await ctx.reply("You must provide at least one tag.")
        return
    tag_list = tags.split()
    settings = get_guild_settings(ctx.guild.id)
    if settings.get("e621_safe_mode") and not ctx.channel.is_nsfw():
        tag_list.append("rating:safe")

    post = fetch_e621_post(tag_list)
    if not post:
        await ctx.reply("No posts found with the given tags.")
        return

    file_url = post.get("file", {}).get("url")
    if not file_url:
        await ctx.reply("The post does not have a valid file URL.")
        return

    file_ext = file_url.split(".")[-1]
    score = post.get("score", {}).get("total", 0)
    tags_str = ", ".join(tag_list)
    post_link = f"https://e621.net/posts/{post['id']}"

    embed = discord.Embed(title=f"Tags: {tags_str}", description=f"Score: {score}", color=discord.Color.green())
    embed.add_field(name="Original Post", value=post_link, inline=False)
    if file_ext in ["jpg", "jpeg", "png", "gif"]:
        embed.set_image(url=file_url)

    await ctx.reply(embed=embed, view=DeleteView())
    if file_ext in ["mp4", "webm"]:
        await ctx.send(file_url)


e621.guild_only = True

def _warn_embed(member: discord.Member, reason: str, warning_id: Optional[int] = None) -> Embed:
    desc = f"{member.mention} has been warned for: **{reason}**"
    if warning_id is not None:
        desc += f"\nWarning ID: `{warning_id}`"
    return Embed(title="Warning Issued", description=desc, color=discord.Color.orange())


@bot.hybrid_command(description="Warn a member.")
@commands.has_permissions(kick_members=True)
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    warning_id = add_warning(ctx.guild.id, member.id, reason)
    await ctx.reply(embed=_warn_embed(member, reason, warning_id))


@bot.hybrid_command(description="Remove a warning by ID.")
@commands.has_permissions(kick_members=True)
async def unwarn(ctx: commands.Context, member: discord.Member, warning_id: int):
    removed = remove_warning(ctx.guild.id, member.id, warning_id)
    if removed:
        embed = Embed(
            title="Warning Removed",
            description=f"The warning with ID `{warning_id}` for {member.mention} has been removed.",
            color=discord.Color.green(),
        )
    else:
        embed = Embed(title="Warning Not Found", description="No matching warning was located.", color=discord.Color.red())
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Remove the last warning for a member.")
@commands.has_permissions(kick_members=True)
async def unwarn_last(ctx: commands.Context, member: discord.Member):
    removed = remove_last_warning(ctx.guild.id, member.id)
    if removed:
        msg = f"The last warning for {member.mention} has been removed."
        color = discord.Color.green()
    else:
        msg = "No warnings found for that member."
        color = discord.Color.red()
    await ctx.reply(embed=Embed(title="Warning Removed", description=msg, color=color))


@bot.hybrid_command(description="View warnings for a member.")
async def warnings(ctx: commands.Context, member: Optional[discord.Member] = None):
    member = member or ctx.author
    warnings_list = list_warnings(ctx.guild.id, member.id)
    if warnings_list:
        warning_text = "\n".join(
            f"ID: {w['id']}, Reason: {w['reason']}, Date: {w['timestamp']}" for w in warnings_list
        )
        color = discord.Color.red()
    else:
        warning_text = "No warnings found."
        color = discord.Color.green()
    embed = Embed(title=f"{member.display_name}'s Warnings", description=warning_text, color=color)
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Timeout a member for a number of minutes.")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx: commands.Context, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
    until = discord.utils.utcnow() + timedelta(minutes=duration)
    await member.edit(timed_out_until=until, reason=reason)
    embed = Embed(
        title="Member Timed Out",
        description=f"{member.mention} has been timed out for {duration} minutes for: **{reason}**",
        color=discord.Color.red(),
    )
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Remove timeout from a member.")
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx: commands.Context, member: discord.Member):
    await member.edit(timed_out_until=None)
    embed = Embed(
        title="Member Untimed Out",
        description=f"{member.mention} is no longer in timeout.",
        color=discord.Color.green(),
    )
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Kick a member.")
@commands.has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    embed = Embed(
        title="Member Kicked",
        description=f"{member.mention} has been kicked for: **{reason}**",
        color=discord.Color.red(),
    )
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Ban a member.")
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    embed = Embed(
        title="Member Banned",
        description=f"{member.mention} has been banned for: **{reason}**",
        color=discord.Color.red(),
    )
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Unban a member using their username and discriminator.")
@commands.has_permissions(ban_members=True)
async def unban(ctx: commands.Context, *, member_name: str):
    banned_users = await ctx.guild.bans()
    try:
        member_name_only, member_discriminator = member_name.split("#")
    except ValueError:
        await ctx.reply("Please provide the member as Username#Discriminator.")
        return

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name_only, member_discriminator):
            await ctx.guild.unban(user)
            embed = Embed(
                title="Member Unbanned",
                description=f"{user.mention} has been unbanned.",
                color=discord.Color.green(),
            )
            await ctx.reply(embed=embed)
            return

    await ctx.reply("User not found.")


@bot.hybrid_command(description="Translate text to English.")
async def translate(ctx: commands.Context, *, text: Optional[str] = None):
    if text:
        text_to_translate = text
    elif ctx.message.reference:
        replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        text_to_translate = replied_message.content
    else:
        messages = [message async for message in ctx.channel.history(limit=2)]
        if len(messages) > 1:
            text_to_translate = messages[1].content
        else:
            await ctx.reply("No text found to translate.")
            return

    detected_language = detect(text_to_translate)
    translated_text = translate_text(text_to_translate)
    embed = Embed(
        title="Translation",
        description=f"**Original ({detected_language}):** {text_to_translate}\n\n**Translated (en):** {translated_text}",
        color=discord.Color.blue(),
    )
    await ctx.reply(embed=embed)


@bot.hybrid_command(description="Retrieve the last deleted message in this channel.")
async def snipe(ctx: commands.Context):
    if ctx.channel.id in _deleted_message_cache:
        message = _deleted_message_cache[ctx.channel.id]
        embed = Embed(description=message.content, color=discord.Color.red(), timestamp=message.created_at)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)
        await ctx.reply(embed=embed)
    else:
        await ctx.reply("There's nothing to snipe.")


@bot.hybrid_command(description="Configure server settings like e621 safe mode and broadcast toggle.")
@commands.has_permissions(manage_guild=True)
async def server_settings(
    ctx: commands.Context,
    e621_safe_mode: Optional[bool] = None,
    broadcast_enabled: Optional[bool] = None,
):
    settings = get_guild_settings(ctx.guild.id)
    if e621_safe_mode is not None:
        settings["e621_safe_mode"] = e621_safe_mode
    if broadcast_enabled is not None:
        settings["broadcast_enabled"] = broadcast_enabled
    save_guild_settings(ctx.guild.id, settings)

    embed = Embed(title="Server Settings Updated", color=discord.Color.blue())
    embed.add_field(name="e621 Safe Mode", value=str(settings["e621_safe_mode"]))
    embed.add_field(name="Broadcast Enabled", value=str(settings["broadcast_enabled"]))
    await ctx.reply(embed=embed)


async def _resolve_message(ctx: commands.Context, message_link: Optional[str]) -> Optional[discord.Message]:
    if message_link:
        parts = message_link.rstrip("/").split("/")
        try:
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                return await channel.fetch_message(message_id)
        except (ValueError, IndexError, AttributeError):
            return None
    if ctx.message.reference:
        return await ctx.channel.fetch_message(ctx.message.reference.message_id)
    messages = [message async for message in ctx.channel.history(limit=2)]
    return messages[1] if len(messages) > 1 else None


@bot.hybrid_command(description="Steal stickers or emojis from another message.")
async def steal(ctx: commands.Context, message_link: Optional[str] = None):
    target_message = await _resolve_message(ctx, message_link)
    if not target_message:
        await ctx.reply("No message found to inspect.")
        return

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
        import re

        custom_emoji_pattern = re.compile(r"<a?:(\w+):(\d+)>")
        match = custom_emoji_pattern.search(target_message.content)
        if match:
            emoji_name, emoji_id = match.groups()
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
            name = emoji_name

    if not emoji_url and not sticker_url:
        await ctx.reply("No custom emoji or sticker found to steal.")
        return

    import re

    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)

    view = discord.ui.View()
    accept_button = discord.ui.Button(label="Accept", style=discord.ButtonStyle.green)
    decline_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.red)

    async def accept_callback(interaction: discord.Interaction):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            await interaction.followup.send("You don't have permission to manage emojis/stickers.", ephemeral=True)
            return
        try:
            if emoji_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(emoji_url) as response:
                        image_data = await response.read()
                        await ctx.guild.create_custom_emoji(name=name, image=image_data)
                await interaction.followup.send(f"Custom emoji :{name}: has been added to the server.")
            elif sticker_url:
                headers = {"Authorization": f"Bot {bot.http.token}"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(sticker_url) as response:
                        sticker_data = await response.read()
                    form_data = aiohttp.FormData()
                    form_data.add_field("name", name)
                    form_data.add_field("tags", "sticker")
                    form_data.add_field("description", "Copied Sticker")
                    form_data.add_field("file", sticker_data, filename="sticker.png", content_type="image/png")
                    upload_url = f"https://discord.com/api/v10/guilds/{ctx.guild.id}/stickers"
                    async with session.post(upload_url, headers=headers, data=form_data) as resp:
                        if resp.status == 201:
                            await interaction.followup.send(f"Sticker {name} has been added to the server.")
                        else:
                            error_text = await resp.text()
                            await interaction.followup.send(f"Failed to add sticker: {resp.status} - {error_text}")
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"Failed to add emoji/sticker: {exc}")

    async def decline_callback(interaction: discord.Interaction):
        await interaction.response.send_message("Operation declined.", ephemeral=True)

    accept_button.callback = accept_callback
    decline_button.callback = decline_callback
    view.add_item(accept_button)
    view.add_item(decline_button)

    embed = discord.Embed(title="Steal Request", description="Do you want to add this custom emoji/sticker to the server?")
    await ctx.reply(embed=embed, view=view)


@bot.hybrid_command(name="help", description="Show available commands.")
async def custom_help(ctx: commands.Context):
    embed = Embed(title="Help - Command List", description="Here are the available commands.", color=discord.Color.blue())
    embed.add_field(
        name="Moderation Commands",
        value="""
        `/warn <user> <reason>` - Warn a member.
        `/unwarn <user> <warning_id>` - Remove a warning by ID.
        `/unwarn_last <user>` - Remove the last warning.
        `/warnings <user>` - Show warnings for a member.
        `/kick <user> <reason>` - Kick a member.
        `/ban <user> <reason>` - Ban a member.
        `/unban <user#tag>` - Unban a member.
        `/timeout <user> <duration>` - Timeout a member.
        `/untimeout <user>` - Remove a member's timeout.
        """,
        inline=False,
    )
    embed.add_field(
        name="Utility Commands",
        value="""
        `/snipe` - Retrieve the last deleted message.
        `/translate <text>` - Translate a message to English.
        `/server_settings` - Configure safe mode and announcements.
        `/steal` - Steal stickers and emojis from other servers.
        """,
        inline=False,
    )
    embed.add_field(
        name="NSFW Command",
        value="`/e621 <tags>` - Fetch a random post from e621.net based on the specified tags (no blacklist).",
        inline=False,
    )
    await ctx.reply(embed=embed)


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN", "BOT_TOKEN_HERE")

    async def main():
        async with bot:
            await bot.start(TOKEN)

    asyncio.run(main())
