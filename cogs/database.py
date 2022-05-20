import pymongo, os, nextcord
from nextcord import Interaction
from nextcord.ext import commands, application_checks

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

#Create a cog for accessing our database
class Database(commands.Cog, name="Database"):
    """Database related commands"""

    COG_EMOJI = "🗂️"

    def __init__(self, bot) -> None:
      self.bot = bot

    @nextcord.slash_command()
    @application_checks.has_permissions(administrator=True)
    async def setrules(self, interaction: Interaction, *, rules: str):
        """Takes the given string as rules for the bot to read. Each rule is punctuated by a semicolon `;`."""
        rule_arr = rules.split("; ")
        db.rules.replace_one({"_id": interaction.guild.id},{"_id": interaction.guild.id, "rules": rule_arr}, upsert=True)
        rule_body = rules.replace("; ", "\n")
        embed = nextcord.Embed(title=f"{interaction.guild.name} Rules", description=rule_body, color=nextcord.Colour.blurple())
        embed.set_footer(text=f"Requested by {interaction.author.name}", icon_url=interaction.author.avatar)
        await interaction.send(embed=embed)
    
    @nextcord.slash_command(guild_ids=[686394755009347655, 579555794933252096, 793685160931098696])
    @application_checks.has_permissions(administrator=True)
    async def birthday(self, interaction: Interaction, member: str, month: int, day: int):
        """Allows you to store a person's birthdate for this server. (Username#1234)"""
        input = {"member":member.capitalize(), "month":month, "day":day}
        if db.birthdays.find_one({"_id": id, "member": member.capitalize()}):
            db['birthdays'].delete_one(input)
            await interaction.send(f"Removed birthday {month}/{day} for {member}.")
        else:
            db['birthdays'].insert_one(input)
            await interaction.send(f"Added birthday {month}/{day} for {member}.")

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Database(bot))