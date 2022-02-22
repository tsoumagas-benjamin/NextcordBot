import nextcord, pymongo, os
from nextcord.ext import commands
import json, requests

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

#Get all the existing collections
collections = db.list_collection_names()

#Function to fetch the quote from an API
def get_quote():
  response = requests.get("https://zenquotes.io/api/random")
  json_data = json.loads(response.text)
  quote = f"*{json_data[0]['q']}*  -  ***{json_data[0]['a']}***"
  return quote

#Function to update entries in keywords
def append_entry(id, category: str, content: str):
    db.keywords.update_one({"_id": id}, {'$push': {category: content}})

#Function to update entries in keywords
def remove_entry(id, category: str, content: str):
    db.keywords.update_one({"_id": id}, {'$pull': {category: content}})

#Function to check if an entry exists and add/remove it
def find_entry(id, category: str, content: str):  
    if db.keywords.find_one({"_id": id, category: content}):
        remove_entry(id, category, content)
        return "Deleted"
    else:
        append_entry(id, category, content)
        return "Added"

#Function to format list entries
def format_entries(entries):
    output = ""
    for entry in entries:
        output += entry
    return entry

#Create a cog for information commands
class Inspiration(commands.Cog, name="Inspiration"):
    """Commands to inspire you"""

    COG_EMOJI = "✨"
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def encouragement(self, ctx, *, message: str):
        """Command to add an encouragement or remove it if it already exists, requires administrator permission
        
        Example: `$encouragement You're great!`"""
        action = find_entry(ctx.guild.id, "encouragements", message)
        await ctx.send(f"{action} encouragement: {message}.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def filter(self, ctx, *, message: str):
        """Command to add an filtered word or remove it if it already exists, requires administrator permission
        
        Example: `$filter bad word`"""
        action = find_entry(ctx.guild.id, "filter", message)
        await ctx.send(f"{action} filter for: {message}.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sad(self, ctx, *, message: str):
        """Command to add a sad word or remove it if it already exists, requires administrator permission
        
        Example: `$sad boo hoo`"""
        action = find_entry(ctx.guild.id, "sad", message)
        await ctx.send(f"{action} sad word: {message}.")
    
    @commands.command(aliases=['resp'])
    @commands.has_permissions(administrator=True)
    async def responding(self, ctx):
        """Command to change the bot's responding status on/off to keywords, requires administrator permission
        
        Example: `$responding on`"""
        current = db.keywords.find_one({"_id": ctx.guild.id})
        new_status = not current["status"]
        db.keywords.update_one({"_id": ctx.guild.id}, {"$set": {"status": new_status}})
        await ctx.send(f"Responding is {new_status}.")
    
    @commands.command()
    async def keywords(self, ctx):
        """Command to give information on all keywords stored for this server
        
        Example: `$keywords`"""
        kw = db.keywords.find_one({"_id": ctx.guild.id})
        sad = kw['sad']
        filtered = kw['filter']
        encourage = kw['encouragements']
        embed = nextcord.Embed(title=f"{ctx.guild.name} Keywords", description="",color=nextcord.Colour.blurple())
        embed.add_field(name="Words that the bot will offer encouragement for:",
                        value=sad,
                        inline=False)
        embed.add_field(name="Words that the bot will try to filter:",
                        value=filtered,
                        inline=False)
        embed.add_field(name="Encouragements the bot can offer:",
                        value=encourage,
                        inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.name}",icon_url=ctx.author.avatar)
        await ctx.send(embed=embed)

    @commands.command()
    async def inspire(self, ctx):
        """Command to return an inspirational quote
        
        Example: `$inspire`"""
        quote = get_quote()
        embed = nextcord.Embed(title='', description=quote, colour=nextcord.Colour.blurple())
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Inspiration(bot))