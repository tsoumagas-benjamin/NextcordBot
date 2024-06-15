import nextcord
import random
from aiohttp import ClientSession
from os import getenv
from re import findall
import requests
import json
import datetime
from pymongo import MongoClient
from nextcord.ext import commands, application_checks, tasks
import urllib.parse as parse
import urllib.request as request
from io import BytesIO

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot 

daily_channel_id = 793685161635741712

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
    12: 31
}

def advice_task():
    advice = None
    while advice is None:
        response = requests.get(url="https://api.adviceslip.com/advice", allow_redirects=False, timeout=20)
        json_data = json.loads(response.text)
        advice = json_data['slip']['advice']
    return advice

def affirm_task():
    affirmation = None
    while affirmation is None:
        response = requests.get(url="https://www.affirmations.dev/", allow_redirects=False, timeout=20)
        json_data = json.loads(response.text)
        affirmation = json_data['affirmation']
    return affirmation

def animal_task():
    animal = None
    while animal is None:
        choices = ["birb", "cats", "dogs", "sadcat", "sillycat"]
        choice = random.choice(choices)
        url = f"https://api.alexflipnote.dev/{choice}"
        response = requests.get(url=url, allow_redirects=False, timeout=20)
        animal = response.json()["file"]
    return animal

# Return list of user ID's who have a birthday today
def birthday_task():
    date = str(datetime.date.today()).split("-")
    month = int(date[1].lstrip("0"))
    day = int(date[2].lstrip("0"))
    #Checks if this day/month combo has a match in the database
    if db.birthdays.find_one({"month": month, "day": day}):
        bday = db.birthdays.find({"month": month, "day": day})
        member_list = []
        # Gets all birthday users ID's
        for member in bday:
            member_list.append(member['_id'])
        return member_list
    else:
        return None

def joke_task():
    url = "https://jokeapi-v2.p.rapidapi.com/joke/Any"
    querystring = {"format":"json","blacklistFlags":"nsfw,racist","safe-mode":"true"}
    key = getenv('JOKE_KEY')
    headers = {
        "X-RapidAPI-Host": "jokeapi-v2.p.rapidapi.com",
        "X-RapidAPI-Key": key
    }
    response = requests.request("GET", url, headers=headers, params=querystring, allow_redirects=False, timeout=20).json()
    jokeType = response["type"]
    jokeCategory = response["category"]
    embed = nextcord.Embed(title=f"{jokeCategory}", color=nextcord.Colour.from_rgb(0, 128, 255))
    if jokeType == "single":
        joke = response["joke"]
        embed.description = joke
    else:
        jokeSetup = response["setup"]
        jokeDelivery = response["delivery"]
        embed.description = f"{jokeSetup}\n\n||{jokeDelivery}||"
    return embed

def meme_task():
    # Get all info about the meme and take the last/best quality image preview
    base_url = "https://meme-api.com/gimme"
    resp = requests.get(url=base_url, allow_redirects=False, timeout=20)
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
        color=nextcord.Colour.from_rgb(0, 128, 255)
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

#Function to fetch the quote from an API
def get_quote():
  response = requests.get(url="https://zenquotes.io/api/random", allow_redirects=False, timeout=20)
  json_data = json.loads(response.text)
  quote = f"*{json_data[0]['q']}*  -  ***{json_data[0]['a']}***"
  return quote

class Fun(commands.Cog, name="Fun"):
    """Commands for your entertainment"""

    COG_EMOJI = "😃"

    def __init__(self, bot):
        self.bot = bot
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
    
    @tasks.loop(time=datetime.time(0))
    async def daily_meme(self):
        # Gets daily meme
        daily_channel = self.bot.get_channel(daily_channel_id)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        await daily_channel.send(embed=meme_task())

    @tasks.loop(time=datetime.time(4))
    async def daily_birthday(self):
        # Gets daily birthday, if any
        daily_channel = self.bot.get_channel(daily_channel_id)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        user_list = birthday_task()
        # Get all user names and mentions formatted
        if user_list is not None:
            # Collect birthday users belonging to the main guild
            bday_message = nextcord.Embed(title=f"🥳\tHappy Birthday!\t🎉", colour=nextcord.Colour.from_rgb(0, 128, 255))
            for user_id in user_list:
                user: nextcord.User = self.bot.get_user(user_id)
                if user is None:
                    user: nextcord.User = await self.bot.fetch_user(user_id)
                # Prune user birthday if no mutual servers exist
                if user.mutual_guilds is None:
                    if db.birthdays.find_one({"_id": user_id}):
                        db.birthdays.delete_one({"_id": user_id})
                else:
                    bday_message.add_field(name="", value=f"**{user.display_name.capitalize()}**")
            await daily_channel.send(embed=bday_message)
    
    @tasks.loop(time=datetime.time(12))
    async def daily_positivity(self):
        # Creates daily positivity post
        daily_channel = self.bot.get_channel(daily_channel_id)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        advice = advice_task()
        affirm = affirm_task()
        quote = get_quote()
        positivity = nextcord.Embed(title=f"😊\tHere's your reminder to stay positive today!\t😊", colour=nextcord.Colour.from_rgb(0, 128, 255))
        positivity.add_field(name="Advice of the day:", value=f"{advice}")
        positivity.add_field(name="Affirmation of the day:", value=f"{affirm}")
        positivity.add_field(name="", value=quote, inline=True)
        await daily_channel.send(embed=positivity)

    @tasks.loop(time=datetime.time(16))
    async def daily_animal(self):
        # Gets daily animal
        try:
            daily_channel = self.bot.get_channel(daily_channel_id)
            if daily_channel is None:
                daily_channel = await self.bot.fetch_channel(daily_channel_id)
            animal = nextcord.Embed(title=f"😊\tHere's your cute animal of the day!\t😊", colour=nextcord.Colour.from_rgb(0, 128, 255))
            animal_url = animal_task()
            animal.set_image(animal_url)
            await daily_channel.send(embed=animal)
        except Exception as e:
            print(f"The error is: {e}")
    
    @tasks.loop(time=datetime.time(20))
    async def daily_joke(self):
        # Gets daily joke
        daily_channel = self.bot.get_channel(daily_channel_id)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        await daily_channel.send(embed=joke_task())

    @nextcord.slash_command()
    async def animal(self, interaction: nextcord.Interaction):
        """Get a random animal picture"""
        result = animal_task()
        await interaction.send(result)

    @nextcord.slash_command()
    async def advice(self, interaction: nextcord.Interaction):
        """Get a random piece of advice"""
        advice = advice_task()
        embed = nextcord.Embed(title=f'Advice for {interaction.user.display_name}:',description=f'{advice}.',color=nextcord.Colour.from_rgb(0, 128, 255))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def affirmation(self, interaction: nextcord.Interaction):
        """Get a random affirmation"""
        affirmation = affirm_task()
        embed = nextcord.Embed(title=f'Affirmation for {interaction.user.display_name}:',description=f'{affirmation}.',color=nextcord.Colour.from_rgb(0, 128, 255))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def birthday(self, interaction: nextcord.Interaction, member: nextcord.Member, month: int, day: int):
        """Allows you to store/overwrite a person's birthdate for this server. If your birthday is February 29th, please write it as February 28th!"""
        if interaction.user is not member and not interaction.user.guild_permissions.administrator:
            return await interaction.send("You cannot set someone else's birthday without admin privileges.")
        if month < 1 or month > 12:
            await interaction.send("Invalid month.")
        elif day < 1 or day > calendar[month]:
            await interaction.send("Invalid day.")
        else:
            input = {"_id": member.id, "month":month, "day":day}
            if db.birthdays.find_one({"_id": member.id}):
                db['birthdays'].replace_one({"_id": member.id}, input)
                await interaction.send(f"Replaced birthday for {member.name}.")
            else:
                db['birthdays'].insert_one(input)
                await interaction.send(f"Added birthday for {member.name}.")

    #Remove this command later, for testing only!
    @nextcord.slash_command()
    async def bday_check(self, interaction: nextcord.Interaction):
        """Testing only: Used to check for today's birthdays"""
        # Gets daily birthday, if any
        user_list = birthday_task()
        # Get all user names and mentions formatted
        if user_list is not None:
            # Collect birthday users belonging to the main guild
            bday_message = nextcord.Embed(title=f"🥳\tHappy Birthday!\t🎉", colour=nextcord.Colour.from_rgb(0, 128, 255))
            for user_id in user_list:
                user: nextcord.User = self.bot.get_user(user_id)
                if user is None:
                    user: nextcord.User = await self.bot.fetch_user(user_id)
                # Prune user birthday if no mutual servers exist
                if user.mutual_guilds is None:
                    if db.birthdays.find_one({"_id": user_id}):
                        db.birthdays.delete_one({"_id": user_id})
                else:
                    bday_message.add_field(name="", value=f"**{user.display_name.capitalize()}**")
            await interaction.send(embed=bday_message)
        else:
            return await interaction.send("No Birthdays today :(")
        
    @nextcord.slash_command()
    async def bored(self, interaction: nextcord.Interaction):
        """Get some activity to cure your boredom"""
        response = requests.get(url="http://www.boredapi.com/api/activity/", allow_redirects=False, timeout=20)
        json_data = json.loads(response.text)
        activity = json_data['activity'].title()
        category = json_data['type'].title()
        embed = nextcord.Embed(title=f'{category.title()}:',description=f'{activity.title()}.',color=nextcord.Colour.from_rgb(0, 128, 255))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def embed(self, interaction: nextcord.Interaction, *, title: str=None, message: str=None,):
        """Create an embed. Type [] in your string to indicate any blank lines you want added to your message."""
        # Allow users to add newlines to their embed messages
        if message is not None:
            split_message = message.split("[]")
            message = "\n".join(split_message)
        embed = nextcord.Embed(title=title, description=message, color=nextcord.Colour.from_rgb(0, 128, 255))
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
                    if r.status in range(200,299):
                        emoji = await interaction.guild.create_custom_emoji(image=val, name=name)
                        await interaction.send(f'Added emoji {name} {emoji}!')
                    else:
                        await interaction.send(f'Could not add emoji. Status: {r.status}.')
                except nextcord.HTTPException:
                    await interaction.send('The emoji is too big!')
                await ses.close()
    
    @nextcord.slash_command()
    async def guessme(self, interaction: nextcord.Interaction, *, name: str):
        """The bot will guess user age, gender, and nationality based on their name using various APIs."""
        #Create results embed
        embed = nextcord.Embed(title=f'Results for {name.title()}',
        description='',color=nextcord.Colour.from_rgb(0, 128, 255))
        #Guess user age
        response = requests.get(f"https://api.agify.io/?name={name}", allow_redirects=False, timeout=20)
        age_data = json.loads(response.text)
        age = age_data['age']
        embed.add_field(name='Predicted age:', value=f'{age}', inline=False)
        #Guess user gender
        response = requests.get(f"https://api.genderize.io/?name={name}", allow_redirects=False, timeout=20)
        gender_data = json.loads(response.text)
        gender, prob = gender_data['gender'], gender_data['probability']
        embed.add_field(name='Predicted gender:', value=f'{gender}', inline=False)
        embed.add_field(name='Probability:', value=f'{prob}', inline=False)
        #Guess user nationality
        response = requests.get(f"https://api.nationalize.io/?name={name}", allow_redirects=False, timeout=20)
        nation_data = json.loads(response.text)
        for country in nation_data['country']:
            country_id, country_prob = country['country_id'], country['probability']
            embed.add_field(name=f'Country {country_id}', value=f'Probability: {country_prob}', inline=False)
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def inspire(self, interaction: nextcord.Interaction):
        """Command to return an inspirational quote"""
        quote = get_quote()
        embed = nextcord.Embed(title='', description=quote, color=nextcord.Colour.from_rgb(0, 128, 255))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def joke(self, interaction: nextcord.Interaction):
        """Gets a random joke from a joke API"""
        result = joke_task()
        await interaction.send(embed=result)

    @nextcord.slash_command()
    async def meme(self, interaction: nextcord.Interaction):
        """Gets a random meme from r/memes, r/dankmemes, or r/me_irl"""
        meme_post = meme_task()
        await interaction.send(embed=meme_post)
      
    @nextcord.slash_command()
    async def viktor(self, interaction: nextcord.Interaction):
        """Gets a random Viktor quote."""
        object = db['Viktor'].aggregate([{ "$sample": { "size": 1 }}])
        for x in object:
            quote = x['quote']
        embed = nextcord.Embed(title="Viktor:", description=f"*{quote}*", color=nextcord.Colour.from_rgb(0, 128, 255))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def youtube(self, interaction: nextcord.Interaction, *, message: str):
        """Search youtube for a video"""
        query_string = parse.urlencode({'search_query': message})
        html_content = request.urlopen('http://www.youtube.com/results?' + query_string)
        search_content = html_content.read().decode()
        search_results = findall(r'\/watch\?v=\w+', search_content)
        await interaction.send('https://www.youtube.com' + search_results[0])

def setup(bot):
    bot.add_cog(Fun(bot))