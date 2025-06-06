import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import commands, application_checks
import requests
import json

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot 

# Create a cog for checking sales on games
class Sales(commands.Cog, name="Game Sales"):
    """Commands for checking for game sales"""

    COG_EMOJI = "💲"

    def __init__(self, bot) -> None:
        self.bot = bot
        
    permitted_guilds = [686394755009347655, 793685160931098696]

    # Dictionary of Game titles and IDs to regularly check for sales
    target_games = {
        "Balatro": "018d937f-700e-7161-9c8d-5423af1b7c99",
        "Blasphemous": "018d937f-046c-70c2-89ad-3db21e19f40f",
        "Blasphemous 2": "018d937f-6ee2-70f6-940c-6212ac74369e",
        "Blasphemous 2 - Mea Culpa DLC": "01921ec1-46fb-71a7-9ccf-c164312fcf97",
        "Death Must Die": "018d937f-701d-7262-bfce-91908d4a68bf",
        "Deep Rock Galactic": "018d937e-fdb1-704e-8962-3e822f2f223e",
        "Elden Ring": "018d937f-590c-728b-ac35-38bcff85f086",
        "Elden Ring - Shadow of the Erdtree DLC": "018dcc3c-5be6-7113-97c8-380547ec6cc3",
        "Hades": "018d937f-33f0-7200-80fc-87f769196c84",
        "Hades II": "018d937f-6ee3-738a-b578-ddd7e9a0d24d",
        "Nine Sols": "018d937f-6ee3-738a-b578-ddd7eb7b327d",
        "Ori and the Blind Forest - Definitive Edition": "018d937f-1919-732b-82d4-9af60320b548",
        "Ori and the Will of the Wisps": "018d937f-3cc5-7116-b8e1-06ca7dd2e7ca",
        "Risk of Rain 2": "018d937f-1ad0-731b-a5bd-1937cb346030",
        "Risk of Rain 2 - Seekers of the Storm DLC": "018d9591-5076-72c7-8f9f-5814e4d41004",
        "Risk of Rain 2 - Survivors of the Void DLC": "018d937f-5db9-7246-b784-e94f402d7cd9",
        "SANABI": "018d937f-62fb-7394-b7df-25ff35798fe6",
        "Terraria": "018d937f-30fa-705e-8a3a-f39719bdde93",
    }
    
    # Function to return a formatted URL to use for the GET request
    def get_base_url(self, substring: str):
        base_url = "https://api.isthereanydeal.com" + substring + "?key=" + getenv('DEAL_KEY')
        return base_url
    
    # Function to get a game's ID on IsThereAnyDeal given it's title
    def get_game_id(self, title: str):
        # Put the game title in lower case, separate each word and then join with +'s
        format_title = "+".join(title.lower().split())

        # Format the URL to query for looking up the game
        base_url = self.get_base_url("/games/lookup/v1")
        query_url = base_url + f"&title={format_title}"

        # Query the API and return the ID field
        game = requests.get(query_url)
        game_json = json.loads(game.content)
        game_id = game_json['game']['id']

        return game_id
    
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
    @nextcord.slash_command(guild_ids=permitted_guilds)
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

    # Function to get the best price for a given game according to IsThereAnyDeal
    @nextcord.slash_command(guild_ids=permitted_guilds)
    async def best_price(self, interaction: nextcord.Interaction, game: str):
        """Searches IsThereAnyDeal for the best discount on a game given a title."""
        # Get the game's ID given its title
        game_id = self.get_game_id(game)

        # Format game ID as a payload and set up header and API URL
        payload = f"[\"{game_id}\"]"
        headers = {"content-type": "application/json"}
        sale_url = self.get_base_url("/games/prices/v3")

        # Make a POST request to the API and load the response as a python iterable object
        sale = requests.post(sale_url, json=payload, headers=headers)
        sale_json = json.loads(sale.content)

        # Gather information on the historic lows for the game's price
        historic_low = sale_json[0]['historyLow']
        all_time = historic_low['all']['amount']
        last_year = historic_low['y1']['amount']
        three_month = historic_low['m3']['amount']
        
        # Gather information on the current best deal according to IsThereAnyDeal
        best_deal = sale_json[0]['deals'][0]
        best_shop = best_deal['shop']['name']
        best_price = best_deal['price']['amount']
        best_cut = best_deal['cut']
        deal_url = best_deal['url']
        regular_price = best_deal['regular']['amount']

        # Create the embed to send with relevant information that was gathered
        price_embed = nextcord.Embed(
            title=f"Sale Information for {game.title()}", 
            description=f"Current best deal at {best_shop} for ${best_price} USD (-{best_cut}%) | {deal_url}",
            color=nextcord.Colour.blurple()
            )
        price_embed.add_field(name="All Time Low", value=f"${all_time} USD")
        price_embed.add_field(name="Last Year Low", value=f"${all_time} USD")
        price_embed.add_field(name="3 Month Low", value=f"${all_time} USD")

        await interaction.send(embed=price_embed)

    # TODO: Automatically notify users when one of the target games are on sale somewhere.
    # Once a day at a certain time, check list of games for sales
    # If sale exceeds regular price or previous sale report that and override previous sale
    # If sale reaches expiration, remove it and set price for that game back to regular

    # Or look into webhook and authentication


def setup(bot):
    bot.add_cog(Sales(bot))