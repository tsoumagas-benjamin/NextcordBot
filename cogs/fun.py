import nextcord
from nextcord import Interaction
from nextcord.ext import commands, application_checks, tasks
import urllib.parse as parse
import urllib.request as request
import random, aiohttp, os, re, requests, json, pymongo, datetime
from io import BytesIO

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

def animal_task():
    choices = ["shibes", "cats", "birds"]
    choice = random.choice(choices)
    url = f"http://shibe.online/api/{choice}?count=1&urls=true&httpsUrls=true"
    response = requests.get(url)
    result = response.text[2:-2]
    return result

def birthday_task():
    date = str(datetime.date.today()).split("-")
    month = int(date[1].lstrip("0"))
    day = int(date[2].lstrip("0"))
    #Checks if this day/month combo has a match in the database
    if db.birthdays.find_one({"month": month, "day": day}):
        bday = db.birthdays.find({"month": month, "day": day})
        member_list = []
        for member in bday:
            member_full = (member['member'].split("#"))
            member_name = member_full[0]
            member_list.append(member_name)
        member_list.sort()
        birthday_people = ", ".join(member_list)
        embed = nextcord.Embed(title="Happy Birthday", description=f"{birthday_people}", color=nextcord.Colour.from_rgb(225, 0, 255))
        return embed
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
    embed = nextcord.Embed(title=f"{jokeCategory}", color=nextcord.Colour.from_rgb(225, 0, 255))
    if jokeType == "single":
        joke = response["joke"]
        embed.description = joke
    else:
        jokeSetup = response["setup"]
        jokeDelivery = response["delivery"]
        embed.description = f"{jokeSetup}\n\n||{jokeDelivery}||"
    return embed

def meme_task():
    memeAPI = request.urlopen('https://meme-api.herokuapp.com/gimme')
    memeData = json.load(memeAPI)

    memeURL = memeData['url']
    memeName = memeData['title']
    memePoster = memeData['author']
    memeSub = memeData['subreddit']
    memeLink = memeData['postLink']
    memeVotes = memeData['ups']

    embed = nextcord.Embed(
        title=memeName, 
        description=f"r/{memeSub} • Posted by u/{memePoster}", 
        color=nextcord.Colour.orange()
    )
    embed.set_image(url=memeURL)
    embed.set_footer(
        text=f"{memeVotes}🔺 • Original post at: {memeLink}"
    )
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
        self.daily_channel = ""
    
    def cog_unload(self):
        self.daily_birthday.cancel()
        self.daily_animal.cancel()
        self.daily_joke.cancel()
        self.daily_meme.cancel()
    
    async def set_task_channel(self):
        if self.daily_channel is "":
            self.daily_channel = await self.bot.fetch_channel(809892274980257812)
            return self.daily_channel
        else:
            return self.daily_channel

    @tasks.loop(time=datetime.time(4))
    async def daily_birthday(self):
        # Gets daily birthday, if any
        #daily_channel = await self.bot.fetch_channel(809892274980257812)
        result = birthday_task()
        if result is not None:
            await self.daily_channel.send(embed=result)
            print(result)
        else:
            print("No birthdays")

    @tasks.loop(time=datetime.time(16))
    async def daily_animal(self):
        # Gets daily animal
        #daily_channel = await self.bot.fetch_channel(809892274980257812)
        await self.daily_channel.send(animal_task())
        print(animal_task())
    
    @tasks.loop(time=datetime.time(20))
    async def daily_joke(self):
        # Gets daily joke
        #daily_channel = await self.bot.fetch_channel(809892274980257812)
        await self.daily_channel.send(embed=joke_task())
        print(joke_task())
    
    @tasks.loop(time=datetime.time(0))
    async def daily_meme(self):
        # Gets daily meme
        #daily_channel = await self.bot.fetch_channel(809892274980257812)
        await self.daily_channel.send(embed=meme_task())
        print(meme_task())

    @nextcord.slash_command()
    async def animal(self, interaction: Interaction):
        """Get a random animal picture"""
        result = animal_task()
        await interaction.send(result)

    @nextcord.slash_command(guild_ids=[686394755009347655, 579555794933252096, 793685160931098696])
    @application_checks.has_permissions(administrator=True)
    async def birthday(self, interaction: Interaction, member: nextcord.Member, month: int, day: int):
        """Allows you to store a person's birthdate for this server."""
        if month < 1 or month > 12:
            await interaction.send("Invalid month.")
        elif day < 1 or day > 31:
            await interaction.send("Invalid day.")
        elif re.findall("[0-9]{4}", member.discriminator):
            username = member.name + "#" + member.discriminator
            input = {"member":username, "month":month, "day":day}
            if db.birthdays.find_one({"member": username}):
                db['birthdays'].replace_one({"member": username})
                await interaction.send(f"Replaced birthday for {member.name}.")
            else:
                db['birthdays'].insert_one(input)
                await interaction.send(f"Added birthday for {member.name}.")
        else:
            await interaction.send(f"Invalid discriminator.")

    @nextcord.slash_command()
    async def bored(self, interaction: Interaction):
        """Get some activity to cure your boredom"""
        response = requests.get("http://www.boredapi.com/api/activity/")
        json_data = json.loads(response.text)
        activity = json_data['activity'].title()
        category = json_data['type'].title()
        embed = nextcord.Embed(title=f'{category.title()}:',description=f'{activity.title()}.',color=nextcord.Colour.from_rgb(225, 0, 255))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def embed(self, interaction: Interaction, *, message: str=None):
        """Turn your message into an embed"""
        embed = nextcord.Embed(title='', description=message, color=nextcord.Colour.from_rgb(225, 0, 255))
        embed.set_footer(icon_url=interaction.user.display_avatar,text=f'Requested by {interaction.user.name}')
        await interaction.send(embed=embed)

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
        base_url = f'https://www.reddit.com/r/{message}/new.json?sort=hot'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(base_url) as r:
                res = await r.json()
                embed.set_image(url=res['data']['children'][random.randint(0, 25)]['data']['url'])
                await interaction.send(embed=embed)
                await cs.close()
    
    @nextcord.slash_command()
    async def guessme(self, interaction: Interaction, *, name: str):
        """The bot will guess user age, gender, and nationality based on their name using various APIs."""
        #Create results embed
        embed = nextcord.Embed(title=f'Results for {name.title()}',
        description='',color=nextcord.Colour.from_rgb(225, 0, 255))
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
        """Gets a random meme from Heroku's meme API"""
        result = meme_task()
        await interaction.send(embed=result)

    @nextcord.slash_command()
    async def velkoz(self, interaction: Interaction):
        """Gets a random Vel'Koz quote."""
        object = db['velkoz'].aggregate([{ "$sample": { "size": 1 }}])
        for x in object:
            quote = x['quote']
        embed = nextcord.Embed(title="Vel'Koz:", description=f"*{quote}*", color=nextcord.Colour.from_rgb(225, 0, 255))
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