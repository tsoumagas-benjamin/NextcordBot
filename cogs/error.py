import nextcord
from nextcord import Interaction
from nextcord.ext import commands

#Create a cog for error handling
class Error(commands.Cog):
    def __init__(self, bot) -> None:
      self.bot = bot

    #Occurs whenever an error appears from a command
    @commands.Cog.listener()
    async def on_command_error(self, interaction: Interaction, error):

        #Error if user misses a necessary command parameter
        if isinstance(error, commands.MissingRequiredArgument):
            message = (f'`{error.param.name}` is a required argument.')

        #Error if command is on cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            message = f'This command is on cooldown. Please try again after {round(error.retry_after, 1)} seconds.'
        
        #Error if a user enters something wrong
        elif isinstance(error, commands.UserInputError):
            message = "Your input was incorrect, please check it and try again."

        #Error when a command is entered that does not exist
        elif isinstance(error, commands.CommandNotFound):
            message = ('Could not find the command.')

        #Error when a user tries a command that is only for the owner
        elif isinstance(error, commands.NotOwner):
            message = ('You need to be the owner to use this.')

        #Error if user lacks permissions
        elif isinstance(error, commands.MissingPermissions):
            message = (f'You need the following permission(s) for that command: {commands.MissingPermissions}.')

        #Error if bot lacks permissions
        elif isinstance(error, commands.BotMissingPermissions):
            message = (f'I need the following permission(s) for that command: {commands.MissingPermissions}.')

        #Error if the command has been run too many times in a short timespan
        elif isinstance(error, commands.MaxConcurrencyReached):
            message = (
                "You are trying to run the same command too often. Please wait a bit before retrying."
            )
        
        else:
          raise error

        embed = nextcord.Embed(title=error, description = message, color=nextcord.Colour.from_rgb(214, 60, 26))
        await interaction.send(embed=embed, delete_after=5)
        await interaction.message.delete(delay=5)

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Error(bot))