import nextcord, pymongo, os
from nextcord import Interaction
from nextcord.ext import commands, application_checks
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

#Functions to update entries in keywords
def append_entry(id, category: str, content: str):
    db.keywords.update_one({"_id": id}, {'$push': {category: content}})

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
    
    @nextcord.slash_command()
    @application_checks.has_permissions(administrator=True)
    async def encouragement(self, interaction: Interaction, *, message: str):
        """Command to add an encouragement or remove it if it already exists"""
        action = find_entry(interaction.guild.id, "encouragements", message)
        await interaction.send(f"{action} encouragement: {message}.")

    @nextcord.slash_command()
    @application_checks.has_permissions(administrator=True)
    async def filter(self, interaction: Interaction, *, message: str):
        """Command to add an filtered word or remove it if it already exists"""
        action = find_entry(interaction.guild.id, "filter", message)
        await interaction.send(f"{action} filter for: {message}.")

    @nextcord.slash_command()
    async def inspire(self, interaction: Interaction):
        """Command to return an inspirational quote"""
        quote = get_quote()
        embed = nextcord.Embed(title='', description=quote, color=nextcord.Colour.from_rgb(214, 60, 26))
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def keywords(self, interaction: Interaction):
        """Command to give information on all keywords stored for this server"""
        kw = db.keywords.find_one({"_id": interaction.guild.id})
        sad = kw['sad']
        filtered = kw['filter']
        encourage = kw['encouragements']
        if not sad:
            sad = "N/a"
        if not filtered:
            filtered = "N/a"
        if not encourage:
            encourage = "N/a"
        embed = nextcord.Embed(title=f"{interaction.guild.name} Keywords", description="", color=nextcord.Colour.from_rgb(214, 60, 26))
        embed.add_field(name="Words that the bot will offer encouragement for:",
                        value= sad,
                        inline=False)
        embed.add_field(name="Words that the bot will try to filter:",
                        value=filtered,
                        inline=False)
        embed.add_field(name="Encouragements the bot can offer:",
                        value=encourage,
                        inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.name}",icon_url=interaction.user.avatar)
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    @commands.has_permissions(administrator=True)
    async def responding(self, interaction: Interaction):
        """Command to change the bot's responding status on/off to keywords"""
        current = db.keywords.find_one({"_id": interaction.guild.id})
        new_status = not current["status"]
        db.keywords.update_one({"_id": interaction.guild.id}, {"$set": {"status": new_status}})
        await interaction.send(f"Responding is {new_status}.")

    @nextcord.slash_command()
    @application_checks.has_permissions(administrator=True)
    async def sad(self, interaction: Interaction, *, message: str):
        """Command to add a sad word or remove it if it already exists"""
        action = find_entry(interaction.guild.id, "sad", message)
        await interaction.send(f"{action} sad word: {message}.")
    
def setup(bot):
    bot.add_cog(Inspiration(bot))