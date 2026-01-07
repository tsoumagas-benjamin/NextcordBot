import nextcord
from random import choice
from aiohttp import ClientSession
from re import findall
from requests import get, request
from json import loads
from datetime import date, time
from nextcord.ext import commands, application_checks, tasks
import urllib.parse as parse
import urllib.request as request
from io import BytesIO
from utilities import db

calendar = {
    1: 31,
    2: 28,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}


def advice_task():
    advice = None
    while advice is None:
        response = get(
            url="https://api.adviceslip.com/advice", allow_redirects=False, timeout=20
        )
        json_data = loads(response.text)
        advice = json_data["slip"]["advice"]
    return advice


def affirm_task():
    affirmation = None
    while affirmation is None:
        response = get(
            url="https://www.affirmations.dev/", allow_redirects=False, timeout=20
        )
        json_data = loads(response.text)
        affirmation = json_data["affirmation"]
    return affirmation


def animal_task():
    animal = None
    while animal is None:
        choices = ["birb", "cats", "dogs", "sadcat", "sillycat"]
        animal_choice = choice(choices)
        url = f"https://api.alexflipnote.dev/{animal_choice}"
        response = get(url=url, allow_redirects=False, timeout=20)
        animal = response.json()["file"]
    return animal


# Return list of user ID's who have a birthday today
def birthday_task():
    full_date = str(date.today()).split("-")
    month = int(full_date[1].lstrip("0"))
    day = int(full_date[2].lstrip("0"))
    # Checks if this day/month combo has a match in the database
    if db.birthdays.find_one({"month": month, "day": day}):
        bday = db.birthdays.find({"month": month, "day": day})
        member_list = []
        # Gets all birthday users ID's
        for member in bday:
            member_list.append(member["_id"])
        return member_list
    else:
        return None


def joke_task():
    joke = None
    while joke is None:
        url = "https://official-joke-api.appspot.com/random_joke"
        response = get(url=url, allow_redirects=False, timeout=20)
        joke_json = response.json()
        category = joke_json["type"].capitalize()
        joke = f"{joke_json['setup']}\n||{joke_json['punchline']}||"
    return joke, category


def meme_task():
    # Get all info about the meme and take the last/best quality image preview
    base_url = "https://meme-api.com/gimme"
    resp = get(url=base_url, allow_redirects=False, timeout=20)
    res = resp.json()
    post_title = res["title"] if res["title"] is not None else " "
    post_author = res["author"]
    post_subreddit = "r/" + res["subreddit"]
    post_link = res["postLink"]
    nsfw = res["nsfw"]
    spoiler = res["spoiler"]
    ups = res["ups"]
    preview = res["preview"][-1]
    embed = nextcord.Embed(
        title=post_title,
        description=f"Posted by {post_author} on {post_subreddit} with 🔺{ups} upvotes.",
        color=nextcord.Colour.from_rgb(0, 128, 255),
    )
    # Handling potentially mature/spoiler memes
    if nsfw is True or spoiler is True:
        preview = f"|| {preview} ||"
    if nsfw is True and spoiler is True:
        warning = "NSFW and spoiler content!"
    elif nsfw is True and spoiler is False:
        warning = "NSFW content!"
    elif nsfw is False and spoiler is True:
        warning = "Spoiler content!"
    else:
        warning = None
    if warning is not None:
        embed.add_field(name="Warning:", value=f"{warning}")
    embed.set_image(url=preview)
    embed.set_footer(text=f"Link to post: {post_link}")
    return embed


# Function to fetch the quote from an API
def get_quote():
    response = get(
        url="https://zenquotes.io/api/random", allow_redirects=False, timeout=20
    )
    json_data = loads(response.text)
    quote = f"*{json_data[0]['q']}*  -  ***{json_data[0]['a']}***"
    return quote


class Fun(commands.Cog, name="Fun"):
    """Commands for your entertainment"""

    COG_EMOJI = "😃"

    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_channels = db.daily_channels.distinct("channel")
        self.daily_birthday.start()
        self.daily_animal.start()
        self.daily_joke.start()
        self.daily_meme.start()
        self.daily_positivity.start()

    def cog_unload(self):
        self.daily_birthday.cancel()
        self.daily_animal.cancel()
        self.daily_joke.cancel()
        self.daily_meme.cancel()
        self.daily_positivity.cancel()

    @tasks.loop(time=time(0))
    async def daily_meme(self):
        try:
            # Fetch the list of enrolled channels to post daily content to
            self.daily_channels = db.daily_channels.distinct("channel")
            # Send a meme to each of the daily channels
            for channel_id in self.daily_channels:
                daily_channel = self.bot.get_channel(channel_id)
                if daily_channel is None:
                    daily_channel = await self.bot.fetch_channel(channel_id)
                await daily_channel.send(embed=meme_task())
        except Exception as e:
            print(f"The meme task error is: {e}")

    @tasks.loop(time=time(4))
    async def daily_birthday(self):
        try:
            # Check for a list of people whose birthday is today, stopping if there are none
            user_list = birthday_task()
            if user_list is not None:
                # Get all daily content guilds and channels
                birthday_channels = db.daily_channels.find({})
                for channel in birthday_channels:
                    # Start the birthday embed for this guild
                    bday_message = nextcord.Embed(
                        title=f"🥳\tHappy Birthday!\t🎉",
                        colour=nextcord.Colour.from_rgb(0, 128, 255),
                    )
                    # Get the target channel from the registered channel IDs stored
                    target_channel = self.bot.get_channel(channel["channel"])
                    if target_channel is None:
                        target_channel = self.bot.fetch_channel(channel["guild"])
                    # Get the target guild from the registered guild IDs stored
                    target_guild: nextcord.Guild = self.bot.get_guild(channel["guild"])
                    if target_guild is None:
                        target_guild: nextcord.Guild = self.bot.fetch_guild(
                            channel["guild"]
                        )
                    # Add each birthday user to the embed if they are in the current guild
                    for user_id in user_list:
                        if target_guild.get_member(user_id) is not None:
                            user: nextcord.User = self.bot.get_user(user_id)
                            if user is None:
                                user: nextcord.User = await self.bot.fetch_user(user_id)
                            bday_message.add_field(
                                name="", value=f"**{user.display_name.capitalize()}**"
                            )
                    # If birthday embed has no fields/no users with birthdays for that server, skip it
                    if bday_message.fields is None:
                        continue
                    # Send the birthday embed for this guild
                    await target_channel.send(embed=bday_message)
        except Exception as e:
            print(f"The birthday task error is: {e}")

    @tasks.loop(time=time(12))
    async def daily_positivity(self):
        try:

            # Creates daily positivity post
            advice = advice_task()
            affirm = affirm_task()
            quote = get_quote()
            positivity = nextcord.Embed(
                title=f"😊\tHere's your reminder to stay positive today!\t😊",
                colour=nextcord.Colour.from_rgb(0, 128, 255),
            )
            positivity.add_field(name="Advice of the day:", value=f"{advice}")
            positivity.add_field(name="Affirmation of the day:", value=f"{affirm}")
            positivity.add_field(name="", value=quote, inline=True)

            # Send some positivity to each of the daily channels
            self.daily_channels = db.daily_channels.distinct("channel")
            for channel_id in self.daily_channels:
                daily_channel = self.bot.get_channel(channel_id)
                if daily_channel is None:
                    daily_channel = await self.bot.fetch_channel(channel_id)
                await daily_channel.send(embed=positivity)

        except Exception as e:
            print(f"The positivity task error is: {e}")

    @tasks.loop(time=time(16))
    async def daily_animal(self):
        # Gets daily animal
        try:

            # Create daily animal post
            animal = nextcord.Embed(
                title=f"😊\tHere's your cute animal of the day!\t😊",
                colour=nextcord.Colour.from_rgb(0, 128, 255),
            )
            animal_url = animal_task()
            animal.set_image(animal_url)

            # Send an animal post to each of the daily channels
            self.daily_channels = db.daily_channels.distinct("channel")
            for channel_id in self.daily_channels:
                daily_channel = self.bot.get_channel(channel_id)
                if daily_channel is None:
                    daily_channel = await self.bot.fetch_channel(channel_id)
                await daily_channel.send(embed=animal)

        except Exception as e:
            print(f"The animal task error is: {e}")

    @tasks.loop(time=time(20))
    async def daily_joke(self):
        # Gets daily joke
        try:
            joke, category = joke_task()
            joke_embed = nextcord.Embed(
                title=f"{category} Joke",
                description=joke,
                color=nextcord.Colour.from_rgb(0, 128, 255),
            )
            # Fetch the list of enrolled channels to post daily content to
            self.daily_channels = db.daily_channels.distinct("channel")
            # Send a cute animal to each of the daily channels
            for channel_id in self.daily_channels:
                daily_channel = self.bot.get_channel(channel_id)
                if daily_channel is None:
                    daily_channel = await self.bot.fetch_channel(channel_id)
                await daily_channel.send(embed=joke_embed)
        except Exception as e:
            print(f"The animal task error is: {e}")

    @nextcord.slash_command()
    async def animal(self, interaction: nextcord.Interaction):
        """Get a random animal picture"""
        result = animal_task()
        await interaction.send(result)

    @nextcord.slash_command()
    async def advice(self, interaction: nextcord.Interaction):
        """Get a random piece of advice"""
        await interaction.send("Gathering advice, please wait.")
        advice = advice_task()
        embed = nextcord.Embed(
            title=f"Advice for {interaction.user.display_name}:",
            description=f"{advice}.",
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )
        await interaction.edit_original_message(content=None, embed=embed)

    @nextcord.slash_command()
    async def affirmation(self, interaction: nextcord.Interaction):
        """Get a random affirmation"""
        affirmation = affirm_task()
        embed = nextcord.Embed(
            title=f"Affirmation for {interaction.user.display_name}:",
            description=f"{affirmation}.",
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def birthday(
        self,
        interaction: nextcord.Interaction,
        member: nextcord.Member,
        month: int,
        day: int,
    ):
        """Allows you to store/overwrite a person's birthdate for this server. If your birthday is February 29th, please write it as February 28th!"""
        if (
            interaction.user is not member
            and not interaction.user.guild_permissions.administrator
        ):
            return await interaction.send(
                "You cannot set someone else's birthday without admin privileges."
            )
        if month < 1 or month > 12:
            await interaction.send("Invalid month.")
        elif day < 1 or day > calendar[month]:
            await interaction.send("Invalid day.")
        else:
            input = {"_id": member.id, "month": month, "day": day}
            if db.birthdays.find_one({"_id": member.id}):
                db["birthdays"].replace_one({"_id": member.id}, input)
                await interaction.send(f"Replaced birthday for {member.name}.")
            else:
                db["birthdays"].insert_one(input)
                await interaction.send(f"Added birthday for {member.name}.")

    @nextcord.slash_command()
    async def edit_embed(
        self,
        interaction: nextcord.Interaction,
        embed_id: str,
        *,
        title: str = None,
        message: str = None,
    ):
        """Edit an embed, will only work if you are the author of the original embed. Type [] in your string to indicate any blank lines you want added to your message."""
        # Get the embed message from the message ID or return an error if it can't be found
        try:
            old_embed: nextcord.Message = await interaction.channel.fetch_message(
                int(embed_id)
            )
        except Exception as e:
            return await interaction.send(content=f"Error: {e}", ephemeral=True)
        # Allow users to add newlines to their embed messages
        if message is not None:
            split_message = message.split("[]")
            message = "\n".join(split_message)
        edited_embed = nextcord.Embed(
            title=title,
            description=message,
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )
        try:
            await old_embed.edit(embed=edited_embed)
            return await interaction.send(
                content=f"Embed with ID: {embed_id} should be updated", ephemeral=True
            )
        except Exception as e:
            return await interaction.send(
                content=f"Unable to update embed with ID: {embed_id}", ephemeral=True
            )

    @nextcord.slash_command()
    async def embed(
        self,
        interaction: nextcord.Interaction,
        *,
        title: str = None,
        message: str = None,
    ):
        """Create an embed. Type [] in your string to indicate any blank lines you want added to your message."""
        # Allow users to add newlines to their embed messages
        if message is not None:
            split_message = message.split("[]")
            message = "\n".join(split_message)
        embed = nextcord.Embed(
            title=title,
            description=message,
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_emojis=True)
    async def getemoji(self, interaction: nextcord.Interaction, url: str, *, name: str):
        """Add an emoji to the server"""
        async with ClientSession() as ses:
            async with ses.get(url) as r:
                try:
                    media = BytesIO(await r.read())
                    val = media.getvalue()
                    if r.status in range(200, 299):
                        emoji = await interaction.guild.create_custom_emoji(
                            image=val, name=name
                        )
                        await interaction.send(f"Added emoji {name} {emoji}!")
                    else:
                        await interaction.send(
                            f"Could not add emoji. Status: {r.status}."
                        )
                except nextcord.HTTPException:
                    await interaction.send("The emoji is too big!")
                await ses.close()

    @nextcord.slash_command()
    async def guessme(self, interaction: nextcord.Interaction, *, name: str):
        """The bot will guess user age, gender, and nationality based on their name using various APIs."""
        # Create results embed
        embed = nextcord.Embed(
            title=f"Results for {name.title()}",
            description="",
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )
        # Guess user age
        response = get(
            f"https://api.agify.io/?name={name}", allow_redirects=False, timeout=20
        )
        age_data = loads(response.text)
        age = age_data["age"]
        embed.add_field(name="Predicted age:", value=f"{age}", inline=False)
        # Guess user gender
        response = get(
            f"https://api.genderize.io/?name={name}", allow_redirects=False, timeout=20
        )
        gender_data = loads(response.text)
        gender, prob = gender_data["gender"], gender_data["probability"]
        embed.add_field(name="Predicted gender:", value=f"{gender}", inline=False)
        embed.add_field(name="Probability:", value=f"{prob}", inline=False)
        # Guess user nationality
        response = get(
            f"https://api.nationalize.io/?name={name}",
            allow_redirects=False,
            timeout=20,
        )
        nation_data = loads(response.text)
        for country in nation_data["country"]:
            country_id, country_prob = country["country_id"], country["probability"]
            embed.add_field(
                name=f"Country {country_id}",
                value=f"Probability: {country_prob}",
                inline=False,
            )
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def inspire(self, interaction: nextcord.Interaction):
        """Command to return an inspirational quote"""
        quote = get_quote()
        embed = nextcord.Embed(
            title="", description=quote, color=nextcord.Colour.from_rgb(0, 128, 255)
        )
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def joke(self, interaction: nextcord.Interaction):
        """Gets a random joke"""
        joke, category = joke_task()
        joke_embed = nextcord.Embed(
            title=f"{category} Joke",
            description=joke,
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )

        await interaction.send(embed=joke_embed)

    @nextcord.slash_command()
    async def meme(self, interaction: nextcord.Interaction):
        """Gets a random meme from r/memes, r/dankmemes, or r/me_irl"""
        meme_post = meme_task()
        await interaction.send(embed=meme_post)

    @nextcord.slash_command()
    async def youtube(self, interaction: nextcord.Interaction, *, message: str):
        """Search youtube for a video"""
        query_string = parse.urlencode({"search_query": message})
        html_content = request.urlopen("http://www.youtube.com/results?" + query_string)
        search_content = html_content.read().decode()
        search_results = findall(r"\/watch\?v=\w+", search_content)
        await interaction.send("https://www.youtube.com" + search_results[0])

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def set_daily_channel(self, interaction: nextcord.Interaction, channel: str):
        """Takes in a channel link/ID and sets it as the automated daily content channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        daily_channel_id = int(channel.split("/")[-1])
        # Prepares the new guild & channel combination for this server
        new_channel = {"guild": interaction.guild_id, "channel": daily_channel_id}
        # Updates the daily channel for the server or inserts it if one doesn't exist currently
        db.daily_channels.replace_one(
            {"guild": interaction.guild_id}, new_channel, upsert=True
        )

        # Let users know where the updated channel is
        updated_channel = interaction.guild.get_channel(interaction.channel_id)
        if updated_channel:
            await interaction.send(
                f"Daily content for this server will go to {updated_channel.name}."
            )

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def remove_daily_channel(self, interaction: nextcord.Interaction):
        """Removes the automated daily content channel for this server, if it exists."""

        # Removes the daily channel for the server if it exists
        if db.daily_channels.find_one({"guild": interaction.guild_id}):
            db.daily_channels.delete_one({"guild": interaction.guild_id})
            await interaction.send(
                "Daily automated content for this server are stopped."
            )
        # Lets the user know if there is no existing daily channel
        else:
            await interaction.send(
                "There is no daily automated content for this server."
            )


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(Fun(bot))
