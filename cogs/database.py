import pymongo, os, nextcord
from nextcord import Interaction
from nextcord.ext import commands, application_checks

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

#Create a cog for error handling
class Database(commands.Cog, name="Database"):
    """Database related commands"""

    COG_EMOJI = "🗂️"

    def __init__(self, bot) -> None:
      self.bot = bot

    @nextcord.slash_command()
    @application_checks.has_permissions(administrator=True)
    async def setrules(self, interaction: Interaction, *, rules: str):
        """Takes the given string as rules for the bot to read. Each rule is punctuated by a semicolon `;`. Requires administrator permission
        
        Example: `$setrules 1. Be respectful!; 2. Don't spam.; 3. Follow the ToS.;`"""
        rule_arr = rules.split("; ")
        db.rules.replace_one({"_id": interaction.guild.id},{"_id": interaction.guild.id, "rules": rule_arr}, upsert=True)
        rule_body = rules.replace("; ", "\n")
        embed = nextcord.Embed(title=f"{interaction.guild.name} Rules", description=rule_body, color=nextcord.Colour.blurple())
        embed.set_footer(text=f"Requested by {interaction.author.name}", icon_url=interaction.author.avatar)
        await interaction.send(embed=embed)

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Database(bot))