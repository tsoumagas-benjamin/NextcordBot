import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import commands, application_checks
import datetime

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot 

# Create a cog for checking sales on games
class Sales(commands.Cog, name="Game Sales"):
    """Commands for checking for game sales"""

    COG_EMOJI = "💲"

    def __init__(self, bot) -> None:
        self.bot = bot
        
    permitted_guilds = [686394755009347655, 793685160931098696]
    
    # Function to return a formatted URL to use for the GET request
    def get_base_url(self, substring: str):
        base_url = "https://api.isthereanydeal.com" + substring + "?key=" + getenv('DEAL_KEY')
        return base_url
    
    # Function to set sales channel for this server
    @nextcord.slash_command(guild_ids=permitted_guilds)
    @application_checks.has_permissions(manage_guild=True)
    async def set_sales_channel(self, interaction: nextcord.Interaction, channel: str):
        """Takes in a channel link/ID and sets it as the automated sales channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        sales_channel_id = int(channel.split("/")[-1])
        # Prepares the new guild & channel combination for this server
        new_channel = {"guild": interaction.guild_id, "channel": sales_channel_id}
        # Updates the sales channel for the server or inserts it if one doesn't exist currently
        db.sales_channels.replace_one({"guild": interaction.guild_id}, new_channel, upsert=True)

        # Let users know where the updated channel is
        updated_channel = interaction.guild.get_channel(sales_channel_id)
        if updated_channel is None:
            updated_channel = await self.bot.fetch_channel(sales_channel_id)
        await interaction.send(f"Sales for this server will go to {updated_channel.name}.")
    
    # Function to remove sales channel for this server
    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def remove_sales_channel(self, interaction: nextcord.Interaction):
        """Removes the automated sales channel for this server, if it exists."""

        # Removes the daily channel for the server if it exists
        if db.sales_channels.find_one({"guild": interaction.guild_id}):
            db.sales_channels.delete_one({"guild": interaction.guild_id})
            await interaction.send("Sales for this server are stopped.")

        # Lets the user know if there is no existing sales channel
        else:
            await interaction.send("There is no sales channel for this server.")

    # TODO: Command to check existing game for best sale from IsThereAnyDeal API

    # TODO: Allow users to enter a list of games they are interested in

    # TODO: Automatically notify a user when one of their requested games are on sale somewhere.


def setup(bot):
    bot.add_cog(Sales(bot))