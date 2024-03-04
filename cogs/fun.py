import nextcord
import random
import aiohttp
import os
import re
import requests
import json
import datetime
import pymongo
from nextcord import Interaction
from nextcord.ext import commands, application_checks, tasks
import urllib.parse as parse
import urllib.request as request
from io import BytesIO

client = pymongo.MongoClient(os.getenv('CONN_STRING')) 
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

def animal_task():
    choices = ["shibes", "cats", "birds"]
    choice = random.choice(choices)
    url = f"http://shibe.online/api/{choice}?count=1&urls=true&httpsUrls=true"
    response = requests.get(url)
    result = response.text[2:-2]
    return result

async def bday_check(self, interaction: Interaction):
        """Testing only: Used to check for today's birthdays"""
        date = str(datetime.date.today()).split("-")
        month = int(date[1].lstrip("0"))
        day = int(date[2].lstrip("0"))
        print(date, month, day)
        #Checks if this day/month combo has a match in the database
        if db.birthdays.find_one({"month": month, "day": day}):
            bday = db.birthdays.find({"month": month, "day": day})
            member_list = []
            # Gets all birthday users ID's
            for member in bday:
                print(member)
                # Get user from ID and check they are still in a server with the bot
                user: nextcord.User = self.bot.get_user(member["_id"])
                if not user:
                    user: nextcord.User = self.bot.fetch_user(member["_id"])
                # Prune user birthday if no mutual servers exist
                if user.mutual_guilds is None:
                    if db.birthdays.find_one({"_id": member["_id"]}):
                        db.birthdays.delete_one({"_id": member["_id"]})
                else:
                    member_list.append(member['_id'])
            print(member_list)

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
            # Get user from ID and check they are still in a server with the bot
            user: nextcord.User = self.bot.get_user(member["_id"])
            if not user:
                user: nextcord.User = self.bot.fetch_user(member["_id"])
            # Prune user birthday if no mutual servers exist
            if member.mutual_guilds is None:
                if db.birthdays.find_one({"_id": member.id}):
                    db.birthdays.delete_one({"_id": member.id})
            else:
                member_list.append(member['_id'])
        return member_list
    else:
        return None

def joke_task():
    url = "https://jokeapi-v2.p.rapidapi.com/joke/Any"
    querystring = {"format":"json","blacklistFlags":"nsfw,racist","safe-mode":"true"}
    key = os.getenv('JOKE_KEY')
    headers = {
        "X-RapidAPI-Host": "jokeapi-v2.p.rapidapi.com",
        "X-RapidAPI-Key": key
    }
    response = requests.request("GET", url, headers=headers, params=querystring).json()
    jokeType = response["type"]
    jokeCategory = response["category"]
    embed = nextcord.Embed(title=f"{jokeCategory}", color=nextcord.Colour.from_rgb(214, 60, 26))
    if jokeType == "single":
        joke = response["joke"]
        embed.description = joke
    else:
        jokeSetup = response["setup"]
        jokeDelivery = response["delivery"]
        embed.description = f"{jokeSetup}\n\n||{jokeDelivery}||"
    return embed

class Fun(commands.Cog, name="Fun"):
    """Commands for your entertainment"""

    COG_EMOJI = "😃"

    def __init__(self, bot):
        self.bot = bot
        self.daily_birthday.start()
        self.daily_animal.start()
        self.daily_joke.start()
        self.daily_meme.start()
    
    def cog_unload(self):
        self.daily_birthday.cancel()
        self.daily_animal.cancel()
        self.daily_joke.cancel()
        self.daily_meme.cancel()

    @tasks.loop(time=datetime.time(4))
    async def daily_birthday(self):
        # Gets daily birthday, if any
        daily_channel = await self.bot.get_channel(daily_channel)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        user_list = birthday_task()
        bday_message = f"🥳\tHappy Birthday!\t🎉\n"
        # Get all user names and mentions formatted
        bday_list = []
        if user_list is not None:
            # Collect birthday users belonging to the main guild
            for user_id in user_list:
                user = await self.bot.get_user(user_id)
                if user is None:
                    user = await self.bot.fetch_user(user_id)
                # Prune user birthday if no mutual servers exist
                if user.mutual_guilds is None:
                    if db.birthdays.find_one({"_id": user_id}):
                        db.birthdays.delete_one({"_id": user_id})
                bday_list.append(f"{user.display_name}")
            bday_message += ("\n".join(bday_list))
            await daily_channel.send(bday_message)

    @tasks.loop(time=datetime.time(16))
    async def daily_animal(self):
        # Gets daily animal
        daily_channel = await self.bot.get_channel(daily_channel_id)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        await daily_channel.send(animal_task())
    
    @tasks.loop(time=datetime.time(20))
    async def daily_joke(self):
        # Gets daily joke
        daily_channel = await self.bot.get_channel(daily_channel_id)
        if daily_channel is None:
            daily_channel = await self.bot.fetch_channel(daily_channel_id)
        await daily_channel.send(embed=joke_task())
    
    @tasks.loop(time=datetime.time(0))
    async def daily_meme(self):
        # Gets daily meme
        base_url = f'https://www.reddit.com/r/memes/hot.json'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(base_url) as r:
                res = await r.json()
                num = random.randint(0, 24)
                post_data = res['data']['children'][num]['data']
                post_title = post_data['title']
                author = post_data['author']
                post_url = post_data['url']
                description = post_data['selftext']
                ups = post_data['ups']
                ratio = post_data['upvote_ratio']
                embed = nextcord.Embed(
                    title=post_title, 
                    description=description,
                    color=nextcord.Colour.from_rgb(214, 60, 26))
                embed.set_image(url=post_url)
                embed.add_field(
                    name=f"🔺{ups} upvotes with a {int(ratio*100)}% upvote ratio", 
                    value=f"Posted by u/{author} [here]({post_url})")
                daily_channel = await self.bot.get_channel(daily_channel_id)
                if daily_channel is None:
                    daily_channel = await self.bot.fetch_channel(daily_channel_id)
                await daily_channel.send(embed=embed)
                await cs.close()

    @nextcord.slash_command()
    async def animal(self, interaction: Interaction):
        """Get a random animal picture"""
        result = animal_task()
        await interaction.send(result)

    @nextcord.slash_command()
    async def birthday(self, interaction: Interaction, member: nextcord.Member, month: int, day: int):
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
    async def bday_check(self, interaction: Interaction):
        """Testing only: Used to check for today's birthdays"""
        date = str(datetime.date.today()).split("-")
        month = int(date[1].lstrip("0"))
        day = int(date[2].lstrip("0"))
        print(date, month, day)
        #Checks if this day/month combo has a match in the database
        if db.birthdays.find_one({"month": month, "day": day}):
            bday = db.birthdays.find({"month": month, "day": day})
            member_list = []
            # Gets all birthday users ID's
            for member in bday:
                print(member)
                # Get user from ID and check they are still in a server with the bot
                user: nextcord.User = self.bot.get_user(member["_id"])
                if not user:
                    user: nextcord.User = self.bot.fetch_user(member["_id"])
                # Prune user birthday if no mutual servers exist
                if user.mutual_guilds is None:
                    if db.birthdays.find_one({"_id": member["_id"]}):
                        db.birthdays.delete_one({"_id": member["_id"]})
                else:
                    member_list.append(member['_id'])
            print(member_list)

    @nextcord.slash_command()
    async def bored(self, interaction: Interaction):
        """Get some activity to cure your boredom"""
        response = requests.get("http://www.boredapi.com/api/activity/")
        json_data = json.loads(response.text)
        activity = json_data['activity'].title()
        category = json_data['type'].title()
        embed = nextcord.Embed(title=f'{category.title()}:',description=f'{activity.title()}.',color=nextcord.Colour.from_rgb(214, 60, 26))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def embed(self, interaction: Interaction, *, message: str=None):
        """Turn your message into an embed"""
        embed = nextcord.Embed(title='', description=message, color=nextcord.Colour.from_rgb(214, 60, 26))
        embed.set_footer(icon_url=interaction.user.display_avatar,text=f'Requested by {interaction.user.name}')
        await interaction.send(embed=embed)
    
    @nextcord.slash_command()
    async def food(self, interaction: Interaction):
        """Search r/food for a random post"""
        base_url = f'https://www.reddit.com/r/food/hot.json'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(base_url) as r:
                res = await r.json()
                num = random.randint(0, 24)
                post_data = res['data']['children'][num]['data']
                post_title = post_data['title']
                author = post_data['author']
                post_url = post_data['url']
                description = post_data['selftext']
                ups = post_data['ups']
                ratio = post_data['upvote_ratio']
                embed = nextcord.Embed(
                    title=post_title, 
                    description=description,
                    color=nextcord.Colour.from_rgb(214, 60, 26))
                embed.set_image(url=post_url)
                embed.add_field(
                    name=f"🔺{ups} upvotes with a {int(ratio*100)}% upvote ratio", 
                    value=f"Posted by u/{author} [here]({post_url})")
                await interaction.send(embed=embed)
                await cs.close()

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_emojis=True)
    async def getemoji(self, interaction: Interaction, url: str, *, name: str):
        """Add an emoji to the server"""
        async with aiohttp.ClientSession() as ses:
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
    async def getpost(self, interaction: Interaction, message: str):
        """Search a subreddit for a random post"""
        embed = nextcord.Embed(title='', description='')
        base_url = f'https://www.reddit.com/r/{message}/hot.json'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(base_url) as r:
                res = await r.json()
                num = random.randint(0, 24)
                post_data = res['data']['children'][num]['data']
                post_title = post_data['title']
                author = post_data['author']
                post_url = post_data['url']
                description = post_data['selftext']
                ups = post_data['ups']
                ratio = post_data['upvote_ratio']
                embed = nextcord.Embed(
                    title=post_title, 
                    description=description,
                    color=nextcord.Colour.from_rgb(214, 60, 26))
                embed.set_image(url=post_url)
                embed.add_field(
                    name=f"🔺{ups} upvotes with a {int(ratio*100)}% upvote ratio", 
                    value=f"Posted by u/{author} [here]({post_url})")
                await interaction.send(embed=embed)
                await cs.close()
    
    @nextcord.slash_command()
    async def guessme(self, interaction: Interaction, *, name: str):
        """The bot will guess user age, gender, and nationality based on their name using various APIs."""
        #Create results embed
        embed = nextcord.Embed(title=f'Results for {name.title()}',
        description='',color=nextcord.Colour.from_rgb(214, 60, 26))
        #Guess user age
        response = requests.get(f"https://api.agify.io/?name={name}")
        age_data = json.loads(response.text)
        age = age_data['age']
        embed.add_field(name='Predicted age:', value=f'{age}', inline=False)
        #Guess user gender
        response = requests.get(f"https://api.genderize.io/?name={name}")
        gender_data = json.loads(response.text)
        gender, prob = gender_data['gender'], gender_data['probability']
        embed.add_field(name='Predicted gender:', value=f'{gender}', inline=False)
        embed.add_field(name='Probability:', value=f'{prob}', inline=False)
        #Guess user nationality
        response = requests.get(f"https://api.nationalize.io/?name={name}")
        nation_data = json.loads(response.text)
        for country in nation_data['country']:
            country_id, country_prob = country['country_id'], country['probability']
            embed.add_field(name=f'Country {country_id}', value=f'Probability: {country_prob}', inline=False)
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def joke(self, interaction: Interaction):
        """Gets a random joke from a joke API"""
        result = joke_task()
        await interaction.send(embed=result)

    @nextcord.slash_command()
    async def meme(self, interaction: Interaction):
        """Gets a random meme from r/memes"""
        embed = nextcord.Embed(title='', description='')
        base_url = f'https://www.reddit.com/r/memes/hot.json'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(base_url) as r:
                res = await r.json()
                num = random.randint(0, 24)
                post_data = res['data']['children'][num]['data']
                post_title = post_data['title']
                author = post_data['author']
                post_url = post_data['url']
                description = post_data['selftext']
                ups = post_data['ups']
                ratio = post_data['upvote_ratio']
                embed = nextcord.Embed(
                    title=post_title, 
                    description=description,
                    color=nextcord.Colour.from_rgb(214, 60, 26))
                embed.set_image(url=post_url)
                embed.add_field(
                    name=f"🔺{ups} upvotes with a {int(ratio*100)}% upvote ratio", 
                    value=f"Posted by u/{author} [here]({post_url})")
                await interaction.send(embed=embed)
                await cs.close()
      
    @nextcord.slash_command()
    async def viktor(self, interaction: Interaction):
        """Gets a random Viktor quote."""
        object = db['Viktor'].aggregate([{ "$sample": { "size": 1 }}])
        for x in object:
            quote = x['quote']
        embed = nextcord.Embed(title="Viktor:", description=f"*{quote}*", color=nextcord.Colour.from_rgb(214, 60, 26))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def youtube(self, interaction: Interaction, *, message: str):
        """Search youtube for a video"""
        query_string = parse.urlencode({'search_query': message})
        html_content = request.urlopen('http://www.youtube.com/results?' + query_string)
        search_content = html_content.read().decode()
        search_results = re.findall(r'\/watch\?v=\w+', search_content)
        await interaction.send('https://www.youtube.com' + search_results[0])

def setup(bot):
    bot.add_cog(Fun(bot))