import nextcord, pymongo, os
from nextcord import Interaction
from nextcord.ext import commands

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

def get_xp(message: nextcord.Message):
    words = message.content.split()
    if len(words) > 5:
        return 5
    else:
        return len(words)

def level_up(xp: int, level: int):
    threshold = level * 25 + 100
    if xp >= threshold:
        return True
    else:
        return False

#Create a cog for image manipulation
class Progress(commands.Cog, name="Progress"):
    """Commands about economy/levelling."""

    COG_EMOJI = "📈"

    def __init__(self, bot) -> None:
      self.bot = bot

    @nextcord.Cog.listener("on_message")
    async def xp(self, message: nextcord.Message):
        if message.author.bot:
            return
        author = message.author
        guild = message.guild
        channel = message.channel
        target = {"_id": author.id, "guild": guild.id}

        # If xp collection doesn't exist for server, make one
        if "levels" not in db.list_collection_names():
            db.create_collection("levels")

        # If member is not registered, create an entry for them
        if not db.levels.find_one(target):
            db.levels.insert_one({"_id": author.id, "guild": guild.id, "level": 0, "xp": 0})
        
        # Increase user xp and level as necessary
        user = db.levels.find_one(target)
        xp = user["xp"] + get_xp(message)
        level = user["level"]
        if level_up(xp, level):
            level += 1
            xp = 0
            await channel.send(f"{author} reached level {level} on {guild}!")
        db.levels.replace_one(target, {"_id": author.id, "guild": guild.id, "level": level, "xp": xp})

    @nextcord.slash_command()
    async def level(self, interaction: Interaction, person: nextcord.Member | nextcord.User | None = None):
        """Check level of a person, defaults to checking your own level"""
        if person is None:
            person = interaction.user
        target = {"_id": person.id, "guild": interaction.guild.id}
        record = db.levels.find_one(target)

        if not record:
            return await interaction.send(f"{person} has no levels or XP!")
        else:
            xp = record["xp"]
            level = record["level"]
            return await interaction.send(f"{person} is level {level} with {xp}XP!")
        
    @nextcord.slash_command()
    async def leaderboard(self, interaction: Interaction):
        """Gets the top 10 highest ranked people on the server"""
        server = interaction.guild
        # Sort the database for the highest 10 scoring on the server
        leaders = db.levels.find({"guild": server}).sort({"level":-1, "xp":-1}).limit(10)
        embed = nextcord.Embed(title=f"{server} Leaderboard", color=nextcord.Colour.from_rgb(214, 60, 26))
        for position, leader in enumerate(leaders):
            # Get relevant information for each of the top 10
            uid = leader["_id"]
            user = self.bot.get_user(uid) if self.bot.get_user(uid) else uid
            xp = leader["xp"]
            level = leader["level"]
            threshold = level * 25 + 100
            embed.add_field(name=f"{position+1}. {uid} Level: {level}", value=f"{xp}/{threshold}XP", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.guild.icon.url)
        await interaction.send(embed=embed)
        
    



#Add the cog to the bot
def setup(bot):
    bot.add_cog(Progress(bot))