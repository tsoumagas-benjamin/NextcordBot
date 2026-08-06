#!/usr/bin/env python
import asyncio
from io import BytesIO
from random import choice

import stoat
from stoat.ext import commands
from youtubesearchpython.future import VideosSearch

from utilities import (
    ChaosBot,
    db,
    delay_until,
    schedule,
    time_from_string,
)


class Fun(commands.Gear, name="Fun"):
    """Commands for your entertainment"""

    GEAR_EMOJI = "😃"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_channels = self.fetch_daily_channels()
        self.loop = asyncio.get_event_loop()

    def gear_load(self):
        self.loop.run_forever(self.daily_fun())

    def gear_unload(self):
        self.loop.stop(self.daily_fun())

    def fetch_daily_channels(self) -> list[str]:
        with db.cursor() as cur:
            cur.execute("SELECT channel_id FROM channels WHERE category = 'daily'")
            daily_channels = cur.fetchall()
        return daily_channels

    async def get_advice(self):
        text_data = await self.bot.client.get_text("https://api.adviceslip.com/advice")
        return text_data["slip"]["advice"]

    async def get_affirmation(self):
        text_data = await self.bot.client.get_text("https://www.affirmations.dev/")
        return text_data["affirmation"]

    async def get_animal(self):
        choices = ["birb", "cats", "dogs", "sadcat", "sillycat"]
        animal_choice = choice(choices)
        json_data = await self.bot.client.get_json(
            f"https://api.alexflipnote.dev/{animal_choice}"
        )
        return json_data["file"]

    async def get_joke(self):
        json_data = await self.bot.client.get_json(
            "https://official-joke-api.appspot.com/random_joke"
        )
        category = json_data["type"].capitalize()
        joke = f"{json_data['setup']}\n||{json_data['punchline']}||"
        return joke, category

    async def get_meme(self):
        # Get all info about the meme and take the last/best quality image preview
        json_data = await self.bot.client.get_json("https://meme-api.com/gimme")
        post_title = json_data["title"] if json_data["title"] is not None else ""
        post_author = json_data["author"]
        post_subreddit = "r/" + json_data["subreddit"]
        post_link = json_data["postLink"]
        nsfw = json_data["nsfw"]
        spoiler = json_data["spoiler"]
        ups = json_data["ups"]
        preview = json_data["preview"][-1]

        description_string = (
            f"Posted by {post_author} on {post_subreddit} with 🔺{ups} upvotes."
        )

        # Handling potentially mature/spoiler memes
        if spoiler is True:
            preview = f"|| {preview} ||"
        if nsfw is True:
            description_string += "\nNSFW content!"

        embed = stoat.SendableEmbed(
            title=post_title,
            description=description_string,
            color="blue",
            icon_url=preview,
            url=post_link,
        )

        return embed

    # Function to fetch the quote from an API
    async def get_quote(self):
        text_data = await self.bot.client.get_text("https://zenquotes.io/api/random")
        quote = f"*{text_data[0]['q']}*  -  ***{text_data[0]['a']}***"
        return quote

    # Function to send content to all the daily channels
    async def send_dailies(self, task_embed: stoat.SendableEmbed):
        # Fetch the list of enrolled channels to post daily content to
        daily_channels = self.fetch_daily_channels()
        # Send a meme to each of the daily channels
        for channel_id in daily_channels:
            daily_channel = self.bot.get_channel(channel_id)
            if daily_channel is None:
                daily_channel = await self.bot.fetch_channel(channel_id)
            await daily_channel.send(embeds=[task_embed])

    async def daily_animal(self):
        # Gets daily animal
        try:
            # Create daily animal post

            animal_picture = await self.get_animal(self.bot.client)
            animal = stoat.SendableEmbed(
                title="😊\tHere's your cute animal of the day!\t😊",
                color="blue",
                media=animal_picture,
            )

            # Get the animal embed and send it to each daily channel
            await self.send_dailies(self.bot, animal)

        except Exception as e:
            print(f"The animal task error is: {e}")

    async def daily_joke(self):
        # Gets daily joke
        try:
            joke, category = await self.get_joke(self.bot.client)
            joke_embed = stoat.SendableEmbed(
                title=f"{category} Joke",
                description=joke,
                color="blue",
            )

            # Get the joke embed and send it to each daily channel
            await self.send_dailies(self.bot, joke_embed)

        except Exception as e:
            print(f"The animal task error is: {e}")

    async def daily_meme(self):
        try:
            # Get the meme embed and send it to each daily channel
            meme_embed: stoat.SendableEmbed = await self.get_meme(self.bot.client)
            await self.send_dailies(self.bot, meme_embed)
        except Exception as e:
            print(f"The meme task error is: {e}")

    async def daily_positivity(self):
        try:
            # Creates daily positivity post
            advice = await self.get_advice(self.bot.client)
            affirm = await self.get_affirmation(self.bot.client)
            quote = await self.get_quote(self.bot.client)
            positivity = stoat.SendableEmbed(
                title="😊\tHere's your reminder to stay positive today!\t😊",
                description=f"Advice of the day:\t{advice}\nAffirmation of the day:\t{affirm}\n{quote}",
                color="blue",
            )

            # Get the positivity embed and send it to each daily channel
            await self.send_dailies(self.bot, positivity)

        except Exception as e:
            print(f"The positivity task error is: {e}")

    # Handle all daily fun tasks
    async def daily_fun(self):
        positivity_task = asyncio.create_task(
            schedule(
                delay=delay_until("Tomorrow", 8),
                loop_time=time_from_string(1, "day"),
                function=self.daily_positivity(),
            )
        )
        animal_task = asyncio.create_task(
            schedule(
                delay=delay_until("Tomorrow", 12),
                loop_time=time_from_string(1, "day"),
                function=self.daily_animal(),
            )
        )
        joke_task = asyncio.create_task(
            schedule(
                delay=delay_until("Tomorrow", 16),
                loop_time=time_from_string(1, "day"),
                function=self.daily_joke(),
            )
        )
        meme_task = asyncio.create_task(
            schedule(
                delay=delay_until("Tomorrow", 20),
                loop_time=time_from_string(1, "day"),
                function=self.daily_meme(),
            )
        )
        await positivity_task
        await animal_task
        await joke_task
        await meme_task

    @commands.command()
    async def animal(self, ctx: commands.Context):
        """Get a random animal picture"""
        result = await self.get_animal(self.bot.client)
        await ctx.channel.send(attachments=[result])

    @commands.command()
    async def advice(self, ctx: commands.Context):
        """Get a random piece of advice"""
        advice = await self.get_advice(self.bot.client)
        embed = stoat.SendableEmbed(
            title=f"Advice for {ctx.author.display_name}:",
            description=f"{advice}.",
            color="blue",
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def affirmation(self, ctx: commands.Context):
        """Get a random affirmation"""
        affirmation = self.get_affirmation()
        embed = stoat.SendableEmbed(
            title=f"Affirmation for {ctx.author.display_name}:",
            description=f"{affirmation}.",
            color="blue",
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    @commands.has_permissions(send_embeds=True)
    async def edit_embed(
        self,
        ctx: commands.Context,
        embed_id: str,
        title: str | None = None,
        message: str | None = None,
    ):
        """Edit an embed, will only work if you are the author of the original embed. Type [] in your string to indicate any blank lines you want added to your message."""
        # Get the embed message from the message ID or return an error if it can't be found
        try:
            old_embed: stoat.Message = ctx.channel.get_message(embed_id)
        except Exception as e:
            return await ctx.channel.send(content=f"Error: {e}", silent=True)
        # Allow users to add newlines to their embed messages
        if message is not None:
            split_message = message.split("[]")
            message = "\n".join(split_message)
        edited_embed = stoat.SendableEmbed(
            title=title,
            description=message,
            color="blue",
        )
        try:
            await old_embed.edit(embeds=[edited_embed])
            return await ctx.channel.send(
                content=f"Embed with ID: {embed_id} should be updated", ephemeral=True
            )
        except Exception as e:
            return await ctx.channel.send(
                content=f"Unable to update embed with ID: {embed_id} due to {e}",
                ephemeral=True,
            )

    @commands.command()
    async def embed(
        self,
        ctx: commands.Context,
        *,
        title: str | None = None,
        message: str | None = None,
    ):
        """Create an embed. Type [] in your string to indicate any blank lines you want added to your message."""
        # Allow users to add newlines to their embed messages
        if message is not None:
            split_message = message.split("[]")
            message = "\n".join(split_message)
        embed = stoat.SendableEmbed(
            title=title,
            description=message,
            color="blue",
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    @commands.has_permissions(manage_customization=True)
    async def getemoji(self, ctx: commands.Context, url: str, *, name: str):
        """Add an emoji to the server"""
        async with self.bot.client.get_bytes(url) as resp:
            try:
                media = BytesIO(await resp.read())
                val = media.getvalue()
                if resp.status in range(200, 299):
                    emoji = await ctx.channel.server.create_custom_emoji(
                        image=val, name=name
                    )
                    await ctx.channel.send(f"Added emoji {name} {emoji}!")
                else:
                    await ctx.channel.send(
                        f"Could not add emoji. Status: {resp.status}."
                    )
            except stoat.HTTPException:
                await ctx.channel.send("The emoji is too big!")

    @commands.command()
    async def guessme(self, ctx: commands.Context, *, name: str):
        """The bot will guess user age, gender, and nationality based on their name using various APIs."""
        # Guess user age
        age_data = await self.bot.client.get_text(f"https://api.agify.io/?name={name}")
        age = age_data["age"]
        embed_description = f"Predicted age: {age}\n"
        # Guess user gender
        gender_data = await self.bot.client.get_text(
            f"https://api.genderize.io/?name={name}"
        )
        gender, prob = gender_data["gender"], gender_data["probability"]
        embed_description += f"Predicted gender: {gender} {prob}% chance\n"
        # Guess user nationality
        nation_data = await self.bot.client.get_text(
            f"https://api.nationalize.io/?name={name}"
        )
        for country in nation_data["country"]:
            country_id, country_prob = country["country_id"], country["probability"]
            embed_description += f"Country {country_id} {country_prob}% chance\n"
        # Create results embed
        embed = stoat.SendableEmbed(
            title=f"Results for {name.title()}",
            description=embed_description,
            color="blue",
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def inspire(self, ctx: commands.Context):
        """Command to return an inspirational quote"""
        quote = self.get_quote()
        embed = stoat.SendableEmbed(title="", description=quote, color="blue")
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def joke(self, ctx: commands.Context):
        """Gets a random joke"""
        joke, category = self.get_joke()
        joke_embed = stoat.SendableEmbed(
            title=f"{category} Joke",
            description=joke,
            color="blue",
        )

        await ctx.channel.send(embeds=[joke_embed])

    @commands.command()
    async def meme(self, ctx: commands.Context):
        """Gets a random meme from r/memes, r/dankmemes, or r/me_irl"""
        meme_post = self.get_meme()
        await ctx.channel.send(embeds=[meme_post])

    @commands.command()
    async def youtube(self, ctx: commands.Context, *, message: str):
        """Search youtube for a video"""
        videos_search = VideosSearch(message, limit=1)
        video_results = await videos_search.next()["result"]
        video_link = video_results[0]["link"]
        await ctx.channel.send(video_link)

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def set_daily_channel(self, ctx: commands.Context, channel_link: str):
        """Takes in a channel link/ID and sets it as the automated daily content channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        channel_id = int(channel_link.split("/")[-1])

        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO channels (server_id, category, channel_id) VALUES (%s, %s, %s) 
                ON CONFLICT (server_id, category) DO UPDATE SET channel_id = EXCLUDED.channel_id""",
                (ctx.server.id, "daily", channel_id),
            )
            db.commit()

        # Let users know where the updated channel is
        updated_channel = ctx.server.get_channel(ctx.channel.channel_id)
        if updated_channel:
            return await ctx.channel.send(
                f"Daily content for this server will go to {updated_channel.name}."
            )

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def remove_daily_channel(self, ctx: commands.Context):
        """Removes the automated daily content channel for this server, if it exists."""

        # Removes the daily channel if it exists
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM channels WHERE (server_id, category) = (%s, %s) LIMIT 1",
                (ctx.server.id, "daily"),
            )
            db.commit()
            if cur.rowcount == 0:
                return await ctx.channel.send(
                    "There is no daily content channel for this server."
                )
            else:
                return await ctx.channel.send(
                    "Daily content for this server is stopped."
                )


async def setup(bot: ChaosBot):
    await bot.add_gear(Fun(bot))
