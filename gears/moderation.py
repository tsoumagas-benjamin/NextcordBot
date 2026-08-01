#!/usr/bin/env python
import stoat
from humanfriendly import parse_timespan
from stoat.ext import commands

from utilities import ChaosBot


# Create a gear for information commands
class Moderation(commands.Gear, name="Moderation"):
    """Commands for moderation"""

    GEAR_EMOJI = "🔨"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member_id: str,
        *,
        reason: str | None = None,
    ):
        """Ban a member from the server"""
        member: stoat.Member = ctx.server.get_member(member_id)
        if reason is None:
            await ctx.channel.send(
                f"{ctx.author.name} has been banned from {ctx.server.name}."
            )
            await member.ban()
        else:
            await ctx.channel.send(
                f"{member.name} has been banned from {ctx.server.name}. Reason: {reason}."
            )
            await member.ban(reason=reason)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 1):
        """Clear a specified amount of messages"""
        for message in range(amount):
            last_message: stoat.Message = ctx.channel.get_last_message()
            last_message.delete()

        await ctx.channel.send(f"Cleared {amount} messages.", ephemeral=True)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member_id: str,
        *,
        reason: str | None = None,
    ):
        """Kick a member from the server"""
        member: stoat.Member = ctx.server.get_member(member_id)
        if reason is None:
            await member.kick()
            await ctx.channel.send(
                f"{member} has been kicked from {ctx.server.server.name}."
            )
        else:
            await member.kick()
            await ctx.channel.send(
                f"{member} has been kicked from {ctx.server.server.name}. Reason: {reason}."
            )

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        member_id: str,
        amount: str,
        *,
        reason: str | None = None,
    ):
        """Timeout a member"""
        member: stoat.Member = ctx.server.get_member(member_id)
        init_time = amount
        await member.timeout(parse_timespan(amount))
        if reason is None:
            await ctx.channel.send(
                f"Member {member.name} has been muted for {init_time}."
            )
        else:
            await ctx.channel.send(
                f"Member {member.name} has been muted for {init_time}. Reason: {reason}."
            )

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, member_id: str):
        """Takes member off the ban list"""
        await ctx.server.unban(member_id)
        await ctx.channel.send(f"Member {member_id} has been unbanned.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx: commands.Context,
        member_id: str,
        *,
        reason: str | None = None,
    ):
        """Removes member from timeout"""
        member: stoat.Member = ctx.server.get_member(member_id)
        await member.timeout(None)
        if reason is None:
            await ctx.channel.send(f"Member {member.name} has been unmuted.")
        else:
            await ctx.channel.send(
                f"Member {member.name} has been unmuted. Reason: {reason}."
            )


def setup(bot: ChaosBot):
    bot.add_gear(Moderation(bot))
