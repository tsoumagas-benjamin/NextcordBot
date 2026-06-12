import stoat
from stoat.ext import commands
from asyncio import sleep
from utilities import ChaosBot


# Create a gear for error handling
class Error(commands.Gear, name="Error"):
    """Listeners for command errors"""

    GEAR_EMOJI = "❌"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot

    # Occurs whenever an error appears from a command
    @commands.Gear.listener()
    async def on_command_error(self, error: commands.CommandErrorEvent):

        # Error if command is on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            message = f"This command is on cooldown. Please try again after {round(error.retry_after, 1)} seconds."

        # Error if a user enters something wrong
        elif isinstance(error, commands.UserInputError):
            message = "Your input was incorrect, please check it and try again."

        # Error when a command is entered that does not exist
        elif isinstance(error, commands.CommandNotFound):
            message = "Could not find the command."

        # Error if the command has been run too many times in a short timespan
        elif isinstance(error, commands.MaxConcurrencyReached):
            message = "You are trying to run the same command too often. Please wait a bit before retrying."

        # Error when a user tries a command that is only for the owner
        elif isinstance(error, commands.NotOwner):
            message = "You need to be the owner to use this."

        # Error if user lacks permissions
        elif isinstance(error, commands.MissingPermissions):
            message = f"You need the following permission(s) for that command: {commands.MissingPermissions}."

        # Error if bot lacks permissions
        elif isinstance(error, commands.BotMissingPermissions):
            message = f"I need the following permission(s) for that command: {commands.MissingPermissions}."

        # Error if user misses a necessary command parameter
        if isinstance(error, commands.MissingRequiredArgument):
            message = f"`{error.param.name}` is a required argument."

        else:
            raise error

        embed = stoat.SendableEmbed(
            title=error,
            description=message,
            color="blue",
        )
        command_error_embed = await error.context.channel.send(embeds=[embed])
        await sleep(5)
        await command_error_embed.delete()


async def setup(bot: ChaosBot):
    bot.add_gear(Error(bot))
