import nextcord
import asyncio
import InfixParser
import time
import os
import pymongo
import matplotlib.pyplot as plt
import numpy as np
from nextcord import Interaction
from nextcord.ext import commands, application_checks

client = pymongo.MongoClient(os.getenv('CONN_STRING')) 
db = client.NextcordBot 

# Class to store poll variables
class Poll:
    def __init__(self):
        self.title: str = ""
        self.embed: nextcord.Embed = None
        self.msg: nextcord.InteractionMessage = None
        self.count: list[int] = [0,0]
        self.colors: list[str] = ["g", "r"]
        
p = Poll()

#Create a cog for information commands
class Information(commands.Cog, name = "Information"):
    """Commands to give you more information"""

    COG_EMOJI = "📗"

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_reaction_add")
    async def vote_add(self, reaction: nextcord.Reaction, user: nextcord.User | nextcord.Member):
        if user.bot or reaction.message.id is p.msg.id:
            return
        # Update count based on reaction
        elif reaction.emoji == "✅":
            p.count[0] += 1
        elif reaction.emoji == "❌":
            p.count[1] += 1
    
    @commands.Cog.listener("on_reaction_remove")
    async def vote_remove(self, reaction: nextcord.Reaction, user: nextcord.User | nextcord.Member):
        if user.bot or reaction.message.id is p.msg.id:
            return
        # Update count based on reaction
        elif reaction.emoji == "✅":
            p.count[0] -= 1
        elif reaction.emoji == "❌":
            p.count[1] -= 1
    
    @nextcord.slash_command()
    async def calculate(self, interaction: Interaction, *, equation: str):
        """Calculates user input and returns the output"""
        equation = equation.replace(" ", "")
        evaluator = InfixParser.Evaluator()
        await interaction.send(f' Result of {equation} is {evaluator.eval(equation)}')
    
    @nextcord.slash_command()
    async def commands(self, interaction: Interaction):
        """Get a list of commands for the bot"""
        commands_list = self.bot.get_application_commands()
        cmds = []
        for cmd in commands_list:
            cmds.append(cmd.qualified_name)
        cmds.sort()
        bot_commands = ", ".join(cmds)
        embed = nextcord.Embed(
            title=f"{self.bot.user.name} Commands",
            description=bot_commands,
            color=nextcord.Colour.from_rgb(214, 60, 26))
        await interaction.send(embed=embed)  

    @nextcord.slash_command()
    async def info(self, interaction: Interaction, member: nextcord.Member):
        """Get information on a user"""
        embed = nextcord.Embed(title=member.display_name,
                               description=member.mention,
                               color=nextcord.Colour.from_rgb(214, 60, 26))
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
        embed = nextcord.Embed(title="Response Times", color=nextcord.Colour.from_rgb(214, 60, 26))
        end_time = time.time()

        embed.add_field(name=f"Ping:", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(name=f"API:", value=f"{round((end_time - start_time) * 1000)}ms")

        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def poll(self, interaction: Interaction, question: str):
        """Create a poll question and have people vote yes or no"""
        # Format embed response to resemble a poll question
        if question[-1] != "?":
            question += "?"
        # Create and send the initial poll embed
        poll_title = f"Poll: {question.capitalize()}"
        poll = nextcord.Embed(title=poll_title, color=nextcord.Colour.from_rgb(214, 60, 26))
        poll.add_field(name="Yes", value="✅", inline=True)
        poll.add_field(name="No", value="❌", inline=True)
        await interaction.send(embed=poll)
        # Fetch the embed and set initial reactions
        msg = await interaction.original_message()
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        # Reset poll variables
        p.title = poll_title
        p.embed = poll
        p.msg = msg
        p.count = [0,0]
    
    @nextcord.slash_command()
    async def pollresults(self, interaction: Interaction):
        """Create a chart of the most recent poll's results"""
        # Make the pie chart, save and close it after
        pie = np.array(p.count)
        plt.pie(pie, colors=p.colors, startangle = 90)
        plt.title(label=p.title, color='w')
        plt.savefig('../poll.png', transparent=True)
        plt.close()
        # Open, send, and close the chart file
        with open("../poll.png", 'rb') as f:
            results = nextcord.File(f)
        await interaction.send(file=results)
        f.close()

    @nextcord.slash_command()
    async def rule(self, interaction: Interaction, number: int):
        """Returns a numbered server rule"""
        if db.rules.find_one({"_id": interaction.guild.id}) != None:
            output = db.rules.find_one({"_id": interaction.guild.id})
            if number < 1 or number >= len(output['rules']):
                await interaction.send(f"Rule {number} doesn't exist!")
                return
            description = output['rules'][number-1]
            embed = nextcord.Embed(title=f"{interaction.guild.name} Rule {number}", description=description, color=nextcord.Colour.from_rgb(214, 60, 26))
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.display_avatar)
            await interaction.send(embed=embed)
        else:
            await interaction.send("You must first set your rules with /setrules!")

    @nextcord.slash_command()
    async def rules(self, interaction: Interaction):
        """Returns all server rules"""
        if db.rules.find_one({"_id": interaction.guild.id}) != None:
            output = db.rules.find_one({"_id": interaction.guild.id})
            description = ""
            for rule in output['rules']:
                description += f"{rule}\n"
            embed = nextcord.Embed(title=f"{interaction.guild.name} Rules", description=description, color=nextcord.Colour.from_rgb(214, 60, 26))
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar)
            await interaction.send(embed=embed)
        else:
            await interaction.send("You must first set your rules with /setrules!")

    @nextcord.slash_command()
    @application_checks.has_permissions(administrator=True)
    async def setrules(self, interaction: Interaction, *, rules: str):
        """Takes the given string as rules for the bot to read. Each rule is punctuated by a semicolon `;`."""
        rule_arr = rules.split("; ")
        db.rules.replace_one({"_id": interaction.guild.id},{"_id": interaction.guild.id, "rules": rule_arr}, upsert=True)
        rule_body = rules.replace("; ", "\n")
        embed = nextcord.Embed(title=f"{interaction.guild.name} Rules", description=rule_body, color=nextcord.Colour.from_rgb(214, 60, 26))
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.display_avatar)
        await interaction.send(embed=embed)

    @nextcord.slash_command(guild_ids=[793685160931098696])
    async def socials(self, interaction: Interaction):
        """Returns links to Ben's socials"""
        embed = nextcord.Embed(title=f"Ben's Socials", color=nextcord.Colour.from_rgb(214, 60, 26))
        embed.add_field(
            name=f"Twitch:", 
            value="https://www.twitch.tv/chaosherald2",
            inline=False)
        embed.add_field(
            name=f"YouTube:", 
            value="https://www.youtube.com/channel/UC147mLQpBtta_ykHdo-fZDw",
            inline=False)
        embed.add_field(
            name=f"Twitter:", 
            value="https://twitter.com/ChaosHerald2",
            inline=False)
        embed.add_field(
            name=f"Instagram:", 
            value="https://www.instagram.com/chaos.herald2/",
            inline=False)
        embed.set_footer(icon_url=interaction.guild.icon.url, text=interaction.guild.name)
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def statistics(self, interaction: Interaction):
        """Returns statistics about the bot"""
        server_count = len(self.bot.guilds)
        total_members = 0
        for guild in self.bot.guilds:
            total_members += guild.member_count
        commands_list = self.bot.get_application_commands()
        cmds = []
        for cmd in commands_list:
            cmds.append(cmd.qualified_name)
        cmds.sort()
        bot_commands = ", ".join(cmds)
        embed = nextcord.Embed(title=f"{self.bot.user.name} Statistics",
                               color=nextcord.Colour.from_rgb(214, 60, 26))
        embed.add_field(name=f"Servers with {self.bot.user.name}: ",
                        value=server_count,
                        inline=False)
        embed.add_field(name=f"{self.bot.user.name} serving: ",
                        value=f"{total_members} users",
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