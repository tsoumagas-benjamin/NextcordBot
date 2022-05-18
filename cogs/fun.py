import nextcord
from nextcord import Interaction
from nextcord.ext import commands
import urllib.parse as parse
import urllib.request as request
import random, aiohttp, re, requests, json
from io import BytesIO

class Fun(commands.Cog, name="Fun"):
    """Commands for your entertainment"""

    COG_EMOJI = "😃"

    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command()
    async def bored(self, interaction):
        """Get some activity to cure your boredom
        
        Example: `$bored`"""
        response = requests.get("http://www.boredapi.com/api/activity/")
        json_data = json.loads(response.text)
        activity = json_data['activity'].title()
        category = json_data['type'].title()
        embed = nextcord.Embed(title=f'{category.title()}:',description=f'{activity.title()}.',colour=nextcord.Colour.blurple())
        await interaction.send(embed=embed)

    @nextcord.slash_command(aliases=['quote'])
    async def embed(self, interaction, *, message: str=None):
        """Turn your message into an embed
        
        Example: `$embed Hello, World!`"""
        embed = nextcord.Embed(title='', description=message, colour=nextcord.Colour.blurple())
        embed.set_footer(icon_url=ctx.author.avatar.url,text=f'Requested by {ctx.author.name}')
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    @commands.has_permissions(manage_emojis=True)
    async def getemoji(self, interaction, url: str, *, name: str):
        """Add an emoji to the server, requires manage emojis permission
        
        Example: `$getemoji https://ggscore.com/media/logo/t62288.png?75 kekW`"""
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
    async def getpost(self, interaction, message: str):
        """Search a subreddit for a random post
        
        Example: `$getpost memes`"""
        embed = nextcord.Embed(title='', description='')
        base_url = f'https://www.reddit.com/r/{message}/new.json?sort=hot'
        async with aiohttp.ClientSession() as cs:
            async with cs.get(base_url) as r:
                res = await r.json()
                embed.set_image(url=res['data']['children'][random.randint(0, 25)]['data']['url'])
                await interaction.send(embed=embed)
                await cs.close()
    
    @nextcord.slash_command()
    async def guessme(self, interaction, *, name: str):
        """The bot will guess user age, gender, and nationality based on their name using various APIs.
        
        Example: `$guessme Ben`"""
        #Create results embed
        embed = nextcord.Embed(title=f'Results for {name.title()}',
        description='',colour=nextcord.Colour.blurple())
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
    async def meme(self, interaction):
        # """Gets a random meme from Heroku's meme API
        
        # Example: `$meme`"""
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
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def youtube(self, interaction, *, message: str):
        """Search youtube for a video
        
        Example: `$youtube Screen Rant`"""
        query_string = parse.urlencode({'search_query': message})
        html_content = request.urlopen('http://www.youtube.com/results?' + query_string)
        search_content = html_content.read().decode()
        search_results = re.findall(r'\/watch\?v=\w+', search_content)
        await interaction.send('https://www.youtube.com' + search_results[0])

def setup(bot):
    bot.add_cog(Fun(bot))