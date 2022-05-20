import pymongo, os, nextcord, re
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
        embed = nextcord.Embed(title=f"{interaction.guild.name} Rules", description=rule_body, color=nextcord.Colour.from_rgb(225, 0, 255))
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.display_avatar)
        await interaction.send(embed=embed)
    
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
                db['birthdays'].delete_one({"member": username})
                await interaction.send(f"Removed birthday for {member.name}.")
            else:
                db['birthdays'].insert_one(input)
                await interaction.send(f"Added birthday for {member.name}.")
        else:
            await interaction.send(f"Invalid discriminator.")

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Database(bot))