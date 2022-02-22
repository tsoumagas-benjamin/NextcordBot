import pymongo, os, nextcord
from nextcord.ext import commands
from main import db

#Create a cog for error handling
class Database(commands.Cog, name="Database"):
    """Database related commands"""

    COG_EMOJI = "🗂️"

    def __init__(self, bot) -> None:
      self.bot = bot
    
    @commands.command(aliases=['setpre'])
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix: str):
        """Changes the bot prefix, requires administrator permission
        
        Example: `$setprefix >`"""
        servers = db.guilds
        servers.replace_one(
            {"_id": ctx.guild.id},{"_id": ctx.guild.id, "prefix": new_prefix}, upsert=True)
        await ctx.send(f"My prefix is: {new_prefix}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setrules(self, ctx, *, rules: str):
        """Takes the given string as rules for the bot to read. Each rule is punctuated by a semicolon `;`. Requires administrator permission
        
        Example: `$setrules 1. Be respectful!; 2. Don't spam.; 3. Follow the ToS.;`"""
        rule_arr = rules.split("; ")
        db.rules.replace_one({"_id": ctx.guild.id},{"_id": ctx.guild.id, "rules": rule_arr}, upsert=True)
        rule_body = rules.replace("; ", "\n")
        embed = nextcord.Embed(title=f"{ctx.guild.name} Rules", description=rule_body, color=nextcord.Colour.blurple())
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar)
        await ctx.send(embed=embed)

        

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Database(bot))