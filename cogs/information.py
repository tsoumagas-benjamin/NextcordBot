import nextcord, pymongo, os
from nextcord.ext import commands
import asyncio, InfixParser, time

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

#Get all the existing collections
collections = db.list_collection_names()

#Create a cog for information commands
class Information(commands.Cog, name = "Information"):
    """Commands to give you more information"""

    COG_EMOJI = "📗"

    def __init__(self, bot):
        self.bot = bot
        self.last_msg = None

    #Stores last deleted message
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        self.last_msg = message
    
    @commands.command(aliases=['calc','eval'])
    async def calculate(self, ctx, *, equation: str):
        """Calculates user input and returns the output
        
        Example: `$calculate 9^0.5 + 6*2 - 8/2`"""
        equation = equation.replace(" ", "")
        evaluator = InfixParser.Evaluator()
        await ctx.send(f' Result is {evaluator.eval(equation)}')

    @commands.command()
    async def ping(self, ctx):
        """Gets bot ping and API response time
        
        Example: `$ping`"""
        start_time = time.time()
        msg = await ctx.send("Testing ping...")
        end_time = time.time()

        await msg.edit(content=f"Ping: {round(self.bot.latency * 1000)}ms \nAPI: {round((end_time - start_time) * 1000)}ms")

    @commands.command()
    async def rule(self, ctx, number: int):
        """Returns a numbered server rule
        
        Example: `$rule 2`"""
        if db.rules.find_one({"_id": ctx.guild.id}) != None:
            output = db.rules.find_one({"_id": ctx.guild.id})
            if number < 1 or number >= len(output['rules']):
                await ctx.send(f"Rule {number} doesn't exist!")
                return
            description = output['rules'][number-1]
            embed = nextcord.Embed(title=f"{ctx.guild.name} Rule {number}", description=description, color=nextcord.Colour.blurple())
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            await ctx.send(embed=embed)
        else:
            await ctx.send("You must first set your rules with $setrules!")

    @commands.command()
    async def rules(self, ctx):
        """Returns all server rules
        
        Example: `$rules`"""
        if db.rules.find_one({"_id": ctx.guild.id}) != None:
            output = db.rules.find_one({"_id": ctx.guild.id})
            description = ""
            for rule in output['rules']:
                description += f"{rule}\n"
            embed = nextcord.Embed(title=f"{ctx.guild.name} Rules", description=description, color=nextcord.Colour.blurple())
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            await ctx.send(embed=embed)
        else:
            await ctx.send("You must first set your rules with $setrules!")
    
    @commands.command()
    async def snipe(self, ctx):
        """Snipes the last deleted message
        
        Example: `$snipe`"""
        if self.last_msg == None:
            await ctx.send("Could not snipe a message!")
            return
        
        author = self.last_msg.author.name
        content = self.last_msg.content
        author_pfp = self.last_msg.author.display_avatar

        embed = nextcord.Embed(title="", description=content, color=nextcord.Colour.blurple())
        embed.set_author(name=author, icon_url=author_pfp)
        await ctx.send(embed=embed)

    @commands.command(aliases=['stat'])
    async def statistics(self, ctx):
        """Returns statistics about the bot
        
        Example: `$statistics`"""
        server_members = len(ctx.guild.humans)
        server_bots = len(ctx.guild.bots)
        server_count = len(self.bot.guilds)
        total_members = 0
        for guild in self.bot.guilds:
            total_members += guild.member_count
        embed = nextcord.Embed(title=f"{self.bot.user.name} Statistics",
                               color=nextcord.Colour.blurple())
        embed.add_field(name=f"{ctx.guild.name} member count: ",
                        value=str(server_members),
                        inline=False)
        embed.add_field(name=f"{ctx.guild.name} bot count: ",
                        value=str(server_bots),
                        inline=False)
        embed.add_field(name=f"Servers with {self.bot.user.name}: ",
                        value=server_count,
                        inline=False)
        embed.add_field(name=f"{self.bot.user.name} serving: ",
                        value=total_members,
                        inline=False)
        embed.set_footer(icon_url=ctx.guild.icon.url, text=ctx.guild.name)
        await ctx.send(embed=embed)

    @commands.command()
    async def timer(self,
                    ctx,
                    amount: int,
                    unit: str, *,
                    description: str = None):
        """Sets a timer with an optional description
        
        Example: `$timer 15 m Snooze`"""
        if description == None:
            description = ''
        letter = unit[:1]
        await ctx.reply(f"Timer {description} set for {amount} {unit}.")
        if letter == "s":
            await asyncio.sleep(amount)
            await ctx.reply(f"Timer {description} is done.")
        elif letter == "m":
            await asyncio.sleep(amount * 60)
            await ctx.reply(f"Timer {description} is done.")
        elif letter == "h":
            await asyncio.sleep(amount * 3600)
            await ctx.reply(f"Timer {description} is done.")
        else:
            await ctx.reply("Please enter a valid unit of time.")

    @commands.command(aliases=['user', 'whois'])
    async def info(self, ctx, member: nextcord.Member):
        """Get information on a user
        
        Example: `$info @PersonalNextcordBot`"""
        embed = nextcord.Embed(title=member.display_name,
                               description=member.mention,
                               color=nextcord.Colour.blurple())
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(
            name="Created at",
            value=member.created_at.strftime("%A, %B %d %Y @ %H:%M:%S %p"),
            inline=False)
        embed.add_field(
            name="Joined at",
            value=member.joined_at.strftime("%A, %B %d %Y @ %H:%M:%S %p"),
            inline=False)
        role_list = []
        for role in member.roles:
            if role.name != "@everyone":
                role_list.append(role.mention)
        embed.add_field(name="Roles", value=', '.join(role_list), inline=False)
        if member.activity != None:
            embed.add_field(name="Activity",
                            value=member.activity,
                            inline=False)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(icon_url=ctx.author.display_avatar,
                         text=f'Requested by {ctx.author.name}')
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Information(bot))