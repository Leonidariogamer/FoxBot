import discord

from discord.ext import commands

from utils import fetch_e621_post  # Adjust to your project structure

from database import get_guild_settings

# Create a Delete Button

class DeleteButton(discord.ui.Button):

    def __init__(self):

        super().__init__(label="Delete", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):

        # Delete the message when the button is pressed

        await interaction.message.delete()

# Create a View to hold the button

class DeleteView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)  # Timeout set to None so the button doesn’t expire

def setup(bot):

    @bot.command(name='e621')

    async def e621(ctx, *tags):

        settings = get_guild_settings(ctx.guild.id)

        if settings['e621_safe_mode'] and not ctx.channel.is_nsfw():

            tags = list(tags) + ['rating:safe']

        if not tags:

            await ctx.send('You must provide at least one tag.')

            return

        post = fetch_e621_post(tags)

        if post:

            file_url = post['file'].get('url')

            if not file_url:

                await ctx.send('The post does not have a valid file URL.')

                return

            file_ext = file_url.split('.')[-1]

            score = post['score']['total']

            tags_str = ', '.join(tags)

            post_link = f"https://e621.net/posts/{post['id']}"

            embed = discord.Embed(title=f"Tags: {tags_str}", description=f"Score: {score}", color=discord.Color.green())

            embed.add_field(name="Original Post", value=post_link, inline=False)

            if file_ext in ['jpg', 'jpeg', 'png', 'gif']:

                embed.set_image(url=file_url)

            # Add the delete button to the post

            view = DeleteView()

            view.add_item(DeleteButton())  # Add the delete button to the view

            # Send the message with the delete button

            await ctx.send(embed=embed, view=view)

            # Send the media file directly if it's a video

            if file_ext in ['mp4', 'webm']:

                await ctx.send(file_url)

        else:

            await ctx.send('No posts found with the given tags.')

