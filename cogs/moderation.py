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
        """Ban a member from the server"""
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
        """Clear a specified amount of messages"""
        await interaction.channel.purge(limit=amount)
        await interaction.send(f"Cleared {amount} messages.", ephemeral = True)

    @nextcord.slash_command()
    @application_checks.has_permissions(kick_members=True)
    async def kick(self, interaction: Interaction, member: nextcord.Member, *, reason: str = None):
        """Kick a member from the server"""
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
        """Timeout a member"""
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
    async def unban(self, interaction: Interaction, *, member):
        """Takes member off the ban list"""
        await interaction.guild.unban(member)
        await interaction.send(f"Member {member.id} has been unbanned.")

    @nextcord.slash_command()
    @application_checks.has_permissions(moderate_members=True)
    async def unmute(self,
                     interaction: Interaction,
                     member: nextcord.Member,
                     *,
                     reason: str = None):
        """Removes member from timeout"""
        await member.edit(timeout=None)
        if reason == None:
            await interaction.send(f"Member {member.name} has been unmuted.")
        else:
            await interaction.send(
                f"Member {member.name} has been unmuted. Reason: {reason}.")


def setup(bot):
    bot.add_cog(Moderation(bot))
