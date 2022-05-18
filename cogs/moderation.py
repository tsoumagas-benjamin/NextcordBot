import nextcord
from nextcord import Interaction
from nextcord.ext import commands, application_checks
import humanfriendly, datetime

#Create a cog for information commands
class Moderation(commands.Cog, name="Moderation"):
    """Commands for moderation"""

    COG_EMOJI = "🔨"
    
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command()
    @application_checks.has_permissions(ban_members=True)
    async def ban(self, interaction: Interaction, member: nextcord.Member, reason: str = None):
        """Ban a member from the server, requires ban members permission
        
        Example: `$ban @PersonalNextcordBot spamming`"""
        if reason is None:
            await interaction.send(
                f"{member.name} has been banned from {interaction.guild.name}.")
            await member.ban()
        else:
            await interaction.send(
                f"{member.name} has been banned from {interaction.guild.name}. Reason: {reason}.")
            await member.ban(reason=reason)

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: Interaction, amount: int = 1):
        """Clear a specified amount of messages, requires manage messages permission
        
        Example: `$clear 5`"""
        await interaction.channel.purge(limit=amount + 1)

    @nextcord.slash_command()
    @application_checks.has_permissions(kick_members=True)
    async def kick(self, interaction: Interaction, member: nextcord.Member, *, reason: str = None):
        """Kick a member from the server, requires kick members permission
        
        Example: `$kick @PersonalNextcordBot spamming`"""
        if reason is None:
            await member.kick()
            await interaction.send(f"{member} has been kicked from {interaction.guild.name}.")
        else:
            await member.kick()
            await interaction.send(
                f"{member} has been kicked from {interaction.guild.name}. Reason: {reason}.")

    @nextcord.slash_command()
    @application_checks.has_permissions(moderate_members=True)
    async def mute(self,
                   interaction: Interaction,
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
            await interaction.send(
                f"Member {member.name} has been muted for {init_time}.")
        else:
            await interaction.send(
                f"Member {member.name} has been muted for {init_time}. Reason: {reason}.")

    @nextcord.slash_command()
    @application_checks.has_permissions(ban_members=True)
    async def unban(self, interaction: Interaction, *, member: nextcord.Member | int):
        """Takes member off the ban list, requires ban members permission
        
        Example: `$unban @PersonalNextcordBot`"""
        await interaction.guild.unban(member)
        await interaction.send(f"Member {member.id} has been unbanned.")

    @nextcord.slash_command()
    @application_checks.has_permissions(moderate_members=True)
    async def unmute(self,
                     interaction: Interaction,
                     member: nextcord.Member,
                     *,
                     reason: str = None):
        """Removes member from timeout, requires moderate members permission
        
        Example: `unmute @PersonalDiscordBot good behaviour`"""
        await member.edit(timeout=None)
        if reason == None:
            await interaction.send(f"Member {member.name} has been unmuted.")
        else:
            await interaction.send(
                f"Member {member.name} has been unmuted. Reason: {reason}.")


def setup(bot):
    bot.add_cog(Moderation(bot))
