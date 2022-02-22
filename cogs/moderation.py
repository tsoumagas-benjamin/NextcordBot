import nextcord
from nextcord.ext import commands
import humanfriendly, datetime

#Create a cog for information commands
class Moderation(commands.Cog, name="Moderation"):
    """Commands for moderation"""

    COG_EMOJI = "🔨"
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['b'])
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: nextcord.Member, reason: str = None):
        """Ban a member from the server, requires ban members permission
        
        Example: `$ban @PersonalNextcordBot spamming`"""
        if reason is None:
            await ctx.send(
                f"{member.name} has been banned from {ctx.guild.name}.")
            await member.ban()
        else:
            await ctx.send(
                f"{member.name} has been banned from {ctx.guild.name}. Reason: {reason}.")
            await member.ban(reason=reason)

    @commands.command(aliases=['c'])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 1):
        """Clear a specified amount of messages, requires manage messages permission
        
        Example: `$clear 5`"""
        await ctx.channel.purge(limit=amount + 1)

    @commands.command(aliases=['k'])
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: nextcord.Member, *, reason: str = None):
        """Kick a member from the server, requires kick members permission
        
        Example: `$kick @PersonalNextcordBot spamming`"""
        if reason is None:
            await member.kick()
            await ctx.send(f"{member} has been kicked from {ctx.guild.name}.")
        else:
            await member.kick()
            await ctx.send(
                f"{member} has been kicked from {ctx.guild.name}. Reason: {reason}.")

    @commands.command(aliases=['m'])
    @commands.has_permissions(moderate_members=True)
    async def mute(self,
                   ctx,
                   member: nextcord.Member,
                   amount: str,
                   *,
                   reason: str = None):
        """Timeout a member, requires moderate members permission
        
        Example: `$mute @PersonalDiscordBot 5m too loud`"""
        init_time = amount
        amount = humanfriendly.parse_timespan(amount)
        await member.edit(timeout=nextcord.utils.utcnow() +
                          datetime.timedelta(seconds=amount))
        if reason == None:
            await ctx.send(
                f"Member {member.name} has been muted for {init_time}.")
        else:
            await ctx.send(
                f"Member {member.name} has been muted for {init_time}. Reason: {reason}.")

    @commands.command(aliases=['ub'])
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member: nextcord.Object):
        """Takes member off the ban list, requires ban members permission
        
        Example: `$unban @PersonalNextcordBot`"""
        await ctx.guild.unban(member)
        await ctx.send(f"Member {member.id} has been unbanned.")

    @commands.command(aliases=['um'])
    @commands.has_permissions(moderate_members=True)
    async def unmute(self,
                     ctx,
                     member: nextcord.Member,
                     *,
                     reason: str = None):
        """Removes member from timeout, requires moderate members permission
        
        Example: `unmute @PersonalDiscordBot good behaviour`"""
        await member.edit(timeout=None)
        if reason == None:
            await ctx.send(f"Member {member.name} has been unmuted.")
        else:
            await ctx.send(
                f"Member {member.name} has been unmuted. Reason: {reason}.")


def setup(bot):
    bot.add_cog(Moderation(bot))
