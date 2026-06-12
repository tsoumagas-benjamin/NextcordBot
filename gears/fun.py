import stoat
from random import choice
from re import findall
from stoat.ext import commands
import urllib.parse as parse
import urllib.request as request
from io import BytesIO
import asyncio
from utilities import (
    ChaosBot,
    db,
    delay_until,
    schedule,
    session,
    time_from_string,
)

# TODO: Switch from MongoDB


async def get_advice(client):
    text_data = await client.get_text("https://api.adviceslip.com/advice")
    return text_data["slip"]["advice"]


async def get_affirmation(client):
    text_data = await client.get_text("https://www.affirmations.dev/")
    return text_data["affirmation"]


async def get_animal(client):
    choices = ["birb", "cats", "dogs", "sadcat", "sillycat"]
    animal_choice = choice(choices)
    json_data = await client.get_json(f"https://api.alexflipnote.dev/{animal_choice}")
    return json_data["file"]


async def get_joke(client):
    json_data = await client.get_json(
        "https://official-joke-api.appspot.com/random_joke"
    )
    category = json_data["type"].capitalize()
    joke = f"{json_data['setup']}\n||{json_data['punchline']}||"
    return joke, category


async def get_meme(client):
    # Get all info about the meme and take the last/best quality image preview
    json_data = await client.get_json("https://meme-api.com/gimme")
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
async def get_quote(client):
    text_data = await client.get_text("https://zenquotes.io/api/random")
    quote = f"*{text_data[0]['q']}*  -  ***{text_data[0]['a']}***"
    return quote


# Function to send content to all the daily channels
async def send_dailies(bot: commands.Bot, task_embed: stoat.SendableEmbed):
    # Fetch the list of enrolled channels to post daily content to
    daily_channels = db.daily_channels.distinct("channel")
    # Send a meme to each of the daily channels
    for channel_id in daily_channels:
        daily_channel = bot.get_channel(channel_id)
        if daily_channel is None:
            daily_channel = await bot.fetch_channel(channel_id)
        await daily_channel.send(embeds=[task_embed])


class Fun(commands.Gear, name="Fun"):
    """Commands for your entertainment"""

    GEAR_EMOJI = "😃"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_channels = db.daily_channels.distinct("channel")
        self.loop = asyncio.get_event_loop()

    def gear_load(self):
        self.loop.run_forever(self.daily_fun())

    def gear_unload(self):
        self.loop.stop(self.daily_fun())

    async def daily_animal(self):
        # Gets daily animal
        try:
            # Create daily animal post

            animal_picture = await get_animal(self.bot.client)
            animal = stoat.SendableEmbed(
                title="😊\tHere's your cute animal of the day!\t😊",
                color="blue",
                media=animal_picture,
            )

            # Get the animal embed and send it to each daily channel
            await send_dailies(self.bot, animal)

        except Exception as e:
            print(f"The animal task error is: {e}")

    async def daily_joke(self):
        # Gets daily joke
        try:
            joke, category = await get_joke(self.bot.client)
            joke_embed = stoat.SendableEmbed(
                title=f"{category} Joke",
                description=joke,
                color="blue",
            )

            # Get the joke embed and send it to each daily channel
            await send_dailies(self.bot, joke_embed)

        except Exception as e:
            print(f"The animal task error is: {e}")

    async def daily_meme(self):
        try:
            # Get the meme embed and send it to each daily channel
            meme_embed: stoat.SendableEmbed = await get_meme(self.bot.client)
            await send_dailies(self.bot, meme_embed)
        except Exception as e:
            print(f"The meme task error is: {e}")

    async def daily_positivity(self):
        try:
            # Creates daily positivity post
            advice = await get_advice(self.bot.client)
            affirm = await get_affirmation(self.bot.client)
            quote = await get_quote(self.bot.client)
            positivity = stoat.SendableEmbed(
                title="😊\tHere's your reminder to stay positive today!\t😊",
                description=f"Advice of the day:\t{advice}\nAffirmation of the day:\t{affirm}\n{quote}",
                color="blue",
            )

            # Get the positivity embed and send it to each daily channel
            await send_dailies(self.bot, positivity)

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
        result = await get_animal(self.bot.client)
        await ctx.channel.send(attachments=[result])

    @commands.command()
    async def advice(self, ctx: commands.Context):
        """Get a random piece of advice"""
        advice = await get_advice(self.bot.client)
        embed = stoat.SendableEmbed(
            title=f"Advice for {ctx.author.display_name}:",
            description=f"{advice}.",
            color="blue",
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def affirmation(self, ctx: commands.Context):
        """Get a random affirmation"""
        affirmation = get_affirmation()
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
        title: str = None,
        message: str = None,
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
        except Exception:
            return await ctx.channel.send(
                content=f"Unable to update embed with ID: {embed_id}", ephemeral=True
            )

    @commands.command()
    async def embed(
        self,
        ctx: commands.Context,
        *,
        title: str = None,
        message: str = None,
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
    @commands.has_permissions(manage_emojis=True)
    async def getemoji(self, ctx: commands.Context, url: str, *, name: str):
        """Add an emoji to the server"""
        async with session.get(url) as resp:
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
        quote = get_quote()
        embed = stoat.SendableEmbed(title="", description=quote, color="blue")
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def joke(self, ctx: commands.Context):
        """Gets a random joke"""
        joke, category = get_joke()
        joke_embed = stoat.SendableEmbed(
            title=f"{category} Joke",
            description=joke,
            color="blue",
        )

        await ctx.channel.send(embeds=[joke_embed])

    @commands.command()
    async def meme(self, ctx: commands.Context):
        """Gets a random meme from r/memes, r/dankmemes, or r/me_irl"""
        meme_post = get_meme()
        await ctx.channel.send(embeds=[meme_post])

    @commands.command()
    async def youtube(self, ctx: commands.Context, *, message: str):
        """Search youtube for a video"""
        query_string = parse.urlencode({"search_query": message})
        html_content = request.urlopen("http://www.youtube.com/results?" + query_string)
        search_content = html_content.read().decode()
        search_results = findall(r"\/watch\?v=\w+", search_content)
        await ctx.channel.send("https://www.youtube.com" + search_results[0])

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def set_daily_channel(self, ctx: commands.Context, channel: str):
        """Takes in a channel link/ID and sets it as the automated daily content channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        daily_channel_id = int(channel.split("/")[-1])
        # Prepares the new server & channel combination for this server
        new_channel = {"server": ctx.channel.server_id, "channel": daily_channel_id}
        # Updates the daily channel for the server or inserts it if one doesn't exist currently
        db.daily_channels.replace_one(
            {"server": ctx.channel.server_id}, new_channel, upsert=True
        )

        # Let users know where the updated channel is
        updated_channel = ctx.channel.server.get_channel(ctx.channel.channel_id)
        if updated_channel:
            await ctx.channel.send(
                f"Daily content for this server will go to {updated_channel.name}."
            )

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def remove_daily_channel(self, ctx: commands.Context):
        """Removes the automated daily content channel for this server, if it exists."""

        # Removes the daily channel for the server if it exists
        if db.daily_channels.find_one({"server": ctx.channel.server_id}):
            db.daily_channels.delete_one({"server": ctx.channel.server_id})
            await ctx.channel.send(
                "Daily automated content for this server are stopped."
            )
        # Lets the user know if there is no existing daily channel
        else:
            await ctx.channel.send(
                "There is no daily automated content for this server."
            )


async def setup(bot: ChaosBot):
    bot.add_gear(Fun(bot))
