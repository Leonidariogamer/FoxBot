import discord
from discord.ext import commands
from tasks.status_tasks import update_status, connect_to_voice_channel
from commands import e621_commands, admin_commands, utility_commands, steal_commands
from database import connect_db

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load commands (synchronously) for non-async commands
e621_commands.setup(bot)           # Load e621 commands
admin_commands.setup(bot)          # Load admin commands
utility_commands.setup(bot)        # Load utility commands
steal_commands.setup(bot)          # Load steal commands

# Load moderation commands asynchronously
async def load_moderation_commands():
    await bot.load_extension('commands.moderation_commands')

@bot.event
async def on_ready():
    print(f"Bot is ready! Serving {len(bot.guilds)} servers.")
    
    # Pass the bot instance to the tasks
    await connect_to_voice_channel(bot)  # Automatically connect to voice channel on startup
    update_status.start(bot)

if __name__ == "__main__":
    connect_db()  # Establish DB connection to MariaDB
    
    # Start the bot and load moderation commands asynchronously
    async def main():
        await load_moderation_commands()  # Load the moderation commands asynchronously
        await bot.start('BOT_TOKEN_HERE')

    import asyncio
    asyncio.run(main())