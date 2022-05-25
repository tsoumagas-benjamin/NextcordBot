import nextcord, pymongo, os
from nextcord import Interaction
from nextcord.ext import commands, application_checks
import asyncio, InfixParser, time
from datetime import datetime

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

    #Stores last deleted message
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        self.last_msg = message
    
    @nextcord.slash_command()
    async def calculate(self, interaction: Interaction, *, equation: str):
        """Calculates user input and returns the output"""
        equation = equation.replace(" ", "")
        evaluator = InfixParser.Evaluator()
        await interaction.send(f' Result of {equation} is {evaluator.eval(equation)}')

    @nextcord.slash_command(guild_ids=[686394755009347655])
    async def date(self, interaction: Interaction):
        """Gets today's date"""
        date_time = datetime.today().strftime("%B %d, %Y")
        await interaction.send(f"Today is: {date_time}")

    @nextcord.slash_command()
    async def info(self, interaction: Interaction, member: nextcord.Member):
        """Get information on a user"""
        embed = nextcord.Embed(title=member.display_name,
                               description=member.mention,
                               color=nextcord.Colour.from_rgb(225, 0, 255))
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
            role_list.reverse()
        embed.add_field(name="Roles", value=', '.join(role_list), inline=False)
        flags = ", ".join(map(str, member.public_flags.all()))
        embed.add_field(name="Public Flags", value=flags, inline=False)
        if member.activity != None:
            embed.add_field(name="Activity",
                            value=member.activity.name,
                            inline=False)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(icon_url=interaction.user.display_avatar,
                         text=f'Requested by {interaction.user.name}')
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def ping(self, interaction: Interaction):
        """Gets bot ping and API response time"""
        start_time = time.time()
        embed = nextcord.Embed(title="Response Times", color=nextcord.Colour.from_rgb(225, 0, 255))
        end_time = time.time()

        embed.add_field(name=f"Ping:", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(name=f"API:", value=f"{round((end_time - start_time) * 1000)}ms")

        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def rule(self, interaction: Interaction, number: int):
        """Returns a numbered server rule"""
        if db.rules.find_one({"_id": interaction.guild.id}) != None:
            output = db.rules.find_one({"_id": interaction.guild.id})
            if number < 1 or number >= len(output['rules']):
                await interaction.send(f"Rule {number} doesn't exist!")
                return
            description = output['rules'][number-1]
            embed = nextcord.Embed(title=f"{interaction.guild.name} Rule {number}", description=description, color=nextcord.Colour.from_rgb(225, 0, 255))
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.display_avatar)
            await interaction.send(embed=embed)
        else:
            await interaction.send("You must first set your rules with $setrules!")

    @nextcord.slash_command()
    async def rules(self, interaction: Interaction):
        """Returns all server rules"""
        if db.rules.find_one({"_id": interaction.guild.id}) != None:
            output = db.rules.find_one({"_id": interaction.guild.id})
            description = ""
            for rule in output['rules']:
                description += f"{rule}\n"
            embed = nextcord.Embed(title=f"{interaction.guild.name} Rules", description=description, color=nextcord.Colour.from_rgb(225, 0, 255))
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar)
            await interaction.send(embed=embed)
        else:
            await interaction.send("You must first set your rules with $setrules!")

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

    @nextcord.slash_command(guild_ids=[686394755009347655, 579555794933252096])
    async def socials(self, interaction: Interaction):
        """Returns links to Olivia's socials"""
        embed = nextcord.Embed(title=f"Olivia's Socials", color=nextcord.Colour.from_rgb(225, 0, 255))
        embed.add_field(
            name=f"Twitch:", 
            value="https://www.twitch.tv/oliviavisentin",
            inline=False)
        embed.add_field(
            name=f"YouTube:", 
            value="https://www.youtube.com/channel/UCk92VCcs2zWzj_bTQ6aeTdg",
            inline=False)
        embed.add_field(
            name=f"Twitter:", 
            value="https://twitter.com/VisentinOlivia",
            inline=False)
        embed.add_field(
            name=f"Instagram:", 
            value="https://www.instagram.com/oliviavisentin/",
            inline=False)
        embed.add_field(
            name=f"Facebook:", 
            value="https://www.facebook.com/olivia.visentin.50",
            inline=False)
        embed.set_footer(icon_url=interaction.guild.icon.url, text=interaction.guild.name)
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def statistics(self, interaction: Interaction):
        """Returns statistics about the bot"""
        server_count = len(self.bot.guilds)
        total_members = len(self.bot.users)
        commands_list = list(dict.fromkeys(self.bot.commands))
        bot_commands = ", ".join(map(str, commands_list))
        print(bot_commands)
        humans = 0
        for u in self.bot.users:
            if not u.bot:
                humans += 1
        embed = nextcord.Embed(title=f"{self.bot.user.name} Statistics",
                               color=nextcord.Colour.from_rgb(225, 0, 255))
        embed.add_field(name=f"Servers with {self.bot.user.name}: ",
                        value=server_count,
                        inline=False)
        embed.add_field(name=f"{self.bot.user.name} serving: ",
                        value=f"{total_members} users\n{humans} humans\n{total_members-humans} bots",
                        inline=False)
        embed.add_field(name=f"{len(commands_list)} commands: ",
                        value=f"{bot_commands}",
                        inline=False)
        embed.set_footer(icon_url=interaction.guild.icon.url, text=interaction.guild.name)
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def timer(self,
                    interaction: Interaction,
                    amount: int,
                    unit: str, *,
                    description: str = None):
        """Sets a timer with an optional description"""
        if description == None:
            description = ''
        else:
            description += " "
        letter = unit[:1]
        await interaction.send(f"Timer {description}set for {amount} {unit}.")
        if letter == "s":
            await asyncio.sleep(amount)
            await interaction.followup.send(f"Timer {description}is done.")
        elif letter == "m":
            await asyncio.sleep(amount * 60)
            await interaction.followup.send(f"Timer {description}is done.")
        elif letter == "h":
            await asyncio.sleep(amount * 3600)
            await interaction.followup.send(f"Timer {description}is done.")
        else:
            await interaction.followup.send("Please enter a valid unit of time.")

def setup(bot):
    bot.add_cog(Information(bot))