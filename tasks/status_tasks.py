from discord.ext import tasks
import discord

# Update bot status periodically (rich presence)
@tasks.loop(minutes=2)
async def update_status(bot):
    server_count = len(bot.guilds)
    status_message = f"Helping in {server_count} servers"
    
    # Set a custom rich presence with a streaming activity
    stream_activity = discord.Streaming(
        name=status_message,  # The custom message displayed
        url="https://www.youtube.com/watch?v=At8v_Yc044Y"  # A valid YouTube streaming URL
    )

    # Apply the streaming activity to the bot
    await bot.change_presence(activity=stream_activity)

# Automatically connect to a voice channel
async def connect_to_voice_channel(bot):
    guild = discord.utils.get(bot.guilds)  # Get the first guild for this example
    if guild:
        voice_channel_id = 1267513398594113587  # Replace with your voice channel ID
        voice_channel = discord.utils.get(guild.voice_channels, id=voice_channel_id)
        if voice_channel:
            vc = await voice_channel.connect()
            print("Connected to voice channel!")
        else:
            print("Voice channel not found.")
    else:
        print("No guild found.")
