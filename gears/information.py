#!/usr/bin/env python
from asyncio import sleep

import aiofiles
import matplotlib.pyplot as plt
import numpy as np
import stoat
from stoat.ext import commands

from utilities import ChaosBot, check_permitted_servers


# Create a gear for information commands
class Information(commands.Gear, name="Information"):
    """Commands to give you more information"""

    GEAR_EMOJI = "📗"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot: commands.Bot = bot
        self.title: str = ""
        self.id: int = 0
        self.count: list[int] = [0, 0]
        self.colors: list[str] = ["g", "r"]

    @commands.Gear.listener()
    async def vote_add(self, on: stoat.MessageReactEvent):
        if on.message.author.bot or on.message_id != self.id:
            return
        # Update count based on reaction
        elif on.emoji == "✅":
            self.count[0] += 1
        elif on.emoji == "❌":
            self.count[1] += 1

    @commands.Gear.listener()
    async def vote_remove(self, on: stoat.MessageUnreactEvent):
        if on.message.author.bot or on.message_id != self.id:
            return
        # Update count based on reaction
        elif on.emoji == "✅":
            self.count[0] -= 1
        elif on.emoji == "❌":
            self.count[1] -= 1

    @commands.command()
    async def calculate(self, ctx: commands.Context, *, equation: str):
        """Calculates user input and returns the output"""
        equation = equation.replace(" ", "")
        evaluation = eval(equation)
        await ctx.channel.send(f" Result of {equation} is {evaluation}")

    @commands.command(name="commands")
    async def get_commands(self, ctx: commands.Context):
        """Get a list of commands for the bot"""
        command_list = self.bot.walk_commands()
        commands = []
        for command in command_list:
            if isinstance(command, stoat.ext.commands.command):
                commands.append(command.qualified_name)
        commands.sort()
        bot_commands = ", ".join(commands)
        embed = stoat.SendableEmbed(
            title=f"{self.bot.user.name} Commands",
            description=bot_commands,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def info(self, ctx: commands.Context, user_id: str):
        """Get information on a user"""
        # Get server member from user ID
        member: stoat.Member = ctx.server.get_member(user_id)

        # Get member's ID, created at date, and joined at date for this server
        info_body = f"ID: {member.id}\n"
        info_body += (
            f"Created at: {member.created_at.strftime('%A, %B %d %Y @ %H:%M:%S %p')}\n"
        )
        info_body += (
            f"Joined at: {member.joined_at.strftime('%A, %B %d %Y @ %H:%M:%S %p')}\n"
        )

        # Get a list of member's roles in this server
        role_list = []
        for role in member.roles:
            if role.name != "@everyone":
                role_list.append(role.mention)
            role_list.reverse()
        info_body += f"Roles: {', '.join(role_list)}\n"

        embed = stoat.SendableEmbed(
            title=f"{member.display_name} {member.mention}",
            description=member.mention,
            color=stoat.Colour.from_rgb(0, 128, 255),
            icon_url=member.server_avatar.url(),
        )

        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Gets bot ping response time"""

        embed = stoat.SendableEmbed(
            title="Ping",
            description=f"{round((stoat.Shard.last_ping_at - stoat.Shard.last_pong_at) * 1000)}ms",
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def poll(self, ctx: commands.Context, question: str):
        """Create a poll question and have people vote yes or no"""
        # Format embed response to resemble a poll question
        if not question.endswith("?"):
            question += "?"
        # Create and send the initial poll embed
        poll_title = f"Poll: {question.capitalize()}"
        poll = stoat.SendableEmbed(
            title=poll_title,
            description="Yes\t✅\nNo\t❌",
            color=stoat.Colour.from_rgb(0, 128, 255),
        )
        message = await ctx.channel.send(embeds=[poll])
        # Set initial reactions
        await message.react("✅")
        await message.react("❌")
        # Reset poll variables
        self.title = poll_title
        self.id = message.id
        self.count = [0, 0]

    @commands.command()
    async def pollresults(self, ctx: commands.Context):
        """Create a chart of the most recent poll's results"""
        # Make the pie chart, save and close it after
        pie = np.array(self.count)
        plt.pie(pie, colors=self.colors, startangle=90)
        plt.title(label=self.title, color="w")
        plt.savefig("../assets/poll.png", bbox_inches=None, transparent=True)
        plt.close()
        # Open, send, and close the chart file
        async with aiofiles.open("../assets/poll.png", mode="rb") as chart:
            await ctx.channel.send(attachments=[chart])

    @commands.command()
    @commands.check(check_permitted_servers)
    async def socials(self, ctx: commands.Context):
        """Returns links to Chaos's socials"""
        embed = stoat.SendableEmbed(
            title="Chaos' Socials", color=stoat.Colour.from_rgb(0, 128, 255)
        )
        twitch_link = "https://www.twitch.tv/chaosherald2"
        youtube_link = "https://www.youtube.com/channel/UC147mLQpBtta_ykHdo-fZDw"
        embed.set_footer(
            icon_url=ctx.channel.server.icon.url(), text=ctx.channel.server.name
        )
        embed = stoat.SendableEmbed(
            title="Chaos' Socials",
            description=f"Twitch: {twitch_link}\nYouTube: {youtube_link}\n{ctx.channel.server.name}",
            color=stoat.Colour.from_rgb(0, 128, 255),
            icon_url=ctx.channel.server.icon.url(),
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def statistics(self, ctx: commands.Context):
        """Returns statistics about the bot"""
        # Get the number of servers with the bot and members in each server
        server_count = len(self.bot.servers)
        total_members = 0
        for name, server in self.bot.servers:
            total_members += len(server.members)

        # Get the list of commands and their qualified names
        commands_list = self.bot.commands
        cmds = []
        for cmd in commands_list:
            cmds.append(cmd.qualified_name)
        cmds.sort()
        bot_commands = ", ".join(cmds)

        # Consolidate statistics info and output the embed
        serving_info = f"Serving {total_members} in {server_count} servers\n"
        commands_info = f"{len(commands_list)} commands:\n{bot_commands}\n"
        embed = stoat.SendableEmbed(
            title=f"{self.bot.user.name} Statistics",
            description=f"{serving_info}{commands_info}{ctx.channel.server.name}",
            color=stoat.Colour.from_rgb(0, 128, 255),
            icon_url=ctx.channel.server.icon.url(),
        )
        await ctx.channel.send(embeds=[embed])

    @commands.command()
    async def timer(
        self,
        ctx: commands.Context,
        amount: int,
        unit: str,
        *,
        description: str | None = None,
    ):
        """Sets a timer with an optional description i.e. 30 s"""
        if description is None:
            description = ""
        else:
            description += " "
        letter = unit[:1].lower()
        timer_set = await ctx.channel.send(
            f"Timer {description}set for {amount} {unit}."
        )

        match letter:
            case "s":
                await sleep(amount)
            case "m":
                await sleep(amount * 60)
            case "h":
                await sleep(amount * 3600)
            case _:
                return await timer_set.reply("Please enter a valid unit of time.")
        return await timer_set.reply(f"Timer {description}is done.")


async def setup(bot: ChaosBot):
    await bot.add_gear(Information(bot))
