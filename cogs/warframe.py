import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import application_checks, commands, tasks
import requests
import json
import datetime
import re

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot
worldstate_url = "https://api.warframe.com/cdn/worldState.php"

# Function to convert an epoch timestamp into a dynamic timestamp
def epoch_convert(epoch: str):
    epoch_num = epoch[:10]
    formatted_time = f"<t:{epoch_num}:f>"
    return formatted_time

# Function to put spaces before capitals in strings
def string_split(string: str):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', string)

# Function to perform a GET request on Warframe's worldstate URL
def request_wf_info(url: str):
    try:
        # Return the parsed JSON as a Python object
        wf_data = requests.get(url)
        wf_world = json.loads(wf_data.content)
        return wf_world
    except requests.exceptions.RequestException as error:
        return error   

# Function to get information on this week's archon hunt
def archon_hunt(url: str, worldstate: dict):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about Archon Hunts
    archon_info = wf_world["LiteSorties"][0]

    # Convert the Archon's arrival and expiry as dynamic timestamps
    archon_start = epoch_convert(archon_info["Activation"]["$date"]["$numberLong"])
    archon_end = epoch_convert(archon_info["Expiry"]["$date"]["$numberLong"])
    archon_duration = f"{archon_start} - {archon_end}"

    # Get the current Archon and the missions leading up to them
    current_archon = worldstate["sortie_bosses"][archon_info["Boss"]]
    archon_missions = archon_info["Missions"]

    hunt_info = []
    # Append each mission type and node
    for mission in archon_missions:
        mission_type = worldstate["mission_type"][mission["missionType"]]
        mission_node = worldstate["nodes"][mission["node"]]
        hunt_info.append(f"{mission_type} - {mission_node}")

    # Create an embed object to return with Archon information
    archon_embed = nextcord.Embed(
        title = f"{current_archon}",
        description = "\n".join(hunt_info),
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )

    archon_embed.set_footer(text=archon_duration)
    return archon_embed

# Function to handle retrieving when Baro Ki'Teer will arrive or if he is here currently
def baro_kiteer(url: str, worldstate: dict, languages: dict):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about Baro Ki'Teer
    baro = wf_world["VoidTraders"][0]

    try:
        # Check if Baro has inventory/is available
        if baro["Manifest"]:
            baro_inventory = baro["Manifest"]
    except:
        # Create an embed object to return with Baro information
        baro_embed = nextcord.Embed(
            title = "Baro Ki'Teer has not arrived yet",
            description = "Inventory Unknown",
            color = nextcord.Colour.from_rgb(0, 128, 255)
        )
        return baro_embed

    # Get the start and end times as dynamic timestamps
    baro_start = epoch_convert(baro["Activation"]["$date"]["$numberLong"])
    baro_end = epoch_convert(baro["Expiry"]["$date"]["$numberLong"])
    baro_duration = f"{baro_start} - {baro_end}"

    # Get Baro's location
    baro_location = worldstate["nodes"][baro["Node"]]

    # Create an embed object to return with Baro information
    baro_embed = nextcord.Embed(
        title = "Baro Ki'Teer is here",
        description = baro_location,
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )

    # Iterate Baro's inventory
    for item in baro_inventory:
        # Get each item's name, ducat, and credit cost
        ducats = item["PrimePrice"]
        credits = item["RegularPrice"]

        # Check if the item is in the dictionary in both regular and lowercase
        if item["ItemType"] in languages:
            name = languages[item["ItemType"]]["value"]
        elif item["ItemType"].lower() in languages:
            name = languages[item["ItemType"].lower()]["value"]
        # Otherwise take the item name as shown
        else:
            name = item["ItemType"].split("/")[-1]
        
        # Format everything into one line and append it to the embed
        baro_embed.add_field(f"{name} - {ducats} D - {credits} C")
    
    baro_embed.set_footer(text=baro_duration)    
    return baro_embed

# Function to handle the retrieval of Duviri information
def duviri_status(url: str):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about Duviri
    duviri = wf_world["EndlessXpChoices"]

    # Look in both regular and steel path variants for reward choices
    regular_choices = duviri[0]["Choices"]
    steel_path_choices = duviri[1]["Choices"]

    # Create an embed object to return with Duviri information
    duviri_embed = nextcord.Embed(
        title = "Weekly Duviri Rewards",
        description = "This week's rewards in the Circuit",
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )

    rewards = []
    sp_rewards = []

    # Get the regular rewards
    for choice in regular_choices:
        rewards.append(f"- {choice}")

    for choice in steel_path_choices:
        sp_rewards.append(f"- {choice} Incarnon Genesis")

    duviri_regular = "\n".join(rewards)
    duviri_steel_path = "\n".join(sp_rewards)

    # Add regular and steel path rewards
    duviri_embed.add_field(
        name="**Circuit Rewards** (Choose one)", 
        value=duviri_regular
    )
    duviri_embed.add_field(
        name="**Steel Path Circuit Rewards** (Choose one)", 
        value=duviri_steel_path
    )

    return duviri_embed

class Warframe(commands.Cog, name="Warframe"):
    """Commands for getting Warframe information"""

    COG_EMOJI = "⚔️"

    def __init__(self, bot):
        self.bot = bot
        # Create a dictionary of Warframe Progenitor types to retrieve later
        self.progenitor = {
            "Impact": ["Baruuk", "Dante", "Gauss", "Grendel", "Rhino", "Sevagoth", "Wukong", "Zephyr"],
            "Heat": ["Chroma", "Ember", "Inaros", "Jade", "Kullervo", "Nezha", "Protea", "Temple", "Vauban", "Wisp"],
            "Cold": ["Frost", "Gara", "Hildryn", "Koumei", "Revenant", "Styanax", "Titania", "Trinity"],
            "Electricity": ["Banshee", "Caliban", "Excalibur", "Gyre", "Limbo", "Nova", "Valkyr", "Volt"],
            "Toxin": ["Atlas", "Dagath", "Ivara", "Khora", "Nekros", "Nidus", "Nokko", "Oberon", "Oraxia", "Saryn"],
            "Magnetic": ["Citrine", "Cyte-09", "Harrow", "Hydroid", "Lavos", "Mag", "Mesa", "Xaku", "Yareli"],
            "Radiation": ["Ash", "Equinox", "Garuda", "Loki", "Mirage", "Nyx", "Octavia", "Qorvex", "Voruna"]
        }
        self.worldstate_url = "https://api.warframe.com/cdn/worldState.php"
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_wf_channels = db.warframe_channels.distinct("channel")
        self.archon_timer.start()
        self.baro_timer.start()
        self.duviri_timer.start()

    def cog_unload(self):
        self.archon_timer.cancel()
        self.baro_timer.cancel()
        self.duviri_timer.cancel()

    # Baro loop runs every Friday to check if Baro has arrived
    @tasks.loop(time=datetime.time(15))
    async def baro_timer(self):
        # Checks every day at 14:00 UTC / 9:00 am EST for Baro Ki'Teer
        weekday = datetime.datetime.today().weekday()
        # If date is Friday, then run the Baro function
        if weekday == 4:
            # Fetch the list of enrolled warframe channels to post daily content to
            self.daily_wf_channels = db.warframe_channels.distinct("channel")
            # Send the content to each of the daily warframe channels
            for channel_id in self.daily_wf_channels:
                daily_wf_channel = self.bot.get_channel(channel_id)
                if daily_wf_channel is None:
                    daily_wf_channel = await self.bot.fetch_channel(channel_id)
                await daily_wf_channel.send(
                    embed=baro_kiteer(self.worldstate_url))

    # Archon loop runs every Sunday for the weekly reset
    @tasks.loop(time=datetime.time(2))
    async def archon_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for Archon Hunts
        weekday = datetime.datetime.today().weekday()
        # If date is Sunday(EST)/Monday(UTC), then run the Archon Hunt function
        if weekday == 0:
            # Fetch the list of enrolled warframe channels to post daily content to
            self.daily_wf_channels = db.warframe_channels.distinct("channel")
            # Send the content to each of the daily warframe channels
            for channel_id in self.daily_wf_channels:
                daily_wf_channel = self.bot.get_channel(channel_id)
                if daily_wf_channel is None:
                    daily_wf_channel = await self.bot.fetch_channel(channel_id)
                await daily_wf_channel.send(embed=archon_hunt(self.worldstate_url))

    # Duviri loop runs every Sunday for the weekly reset
    @tasks.loop(time=datetime.time(2))
    async def duviri_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for Duviri Rewards
        weekday = datetime.datetime.today().weekday()
        # If date is Sunday(EST)/Monday(UTC), then run the Duviri rewards function
        if weekday == 0:
            # Fetch the list of enrolled warframe channels to post daily content to
            self.daily_wf_channels = db.warframe_channels.distinct("channel")
            # Send the content to each of the daily warframe channels
            for channel_id in self.daily_wf_channels:
                daily_wf_channel = self.bot.get_channel(channel_id)
                if daily_wf_channel is None:
                    daily_wf_channel = await self.bot.fetch_channel(channel_id)
                await daily_wf_channel.send(embed=duviri_status(self.worldstate_url))

    @nextcord.slash_command()
    async def archon(self, interaction: nextcord.Interaction):
        """Find the current Archon, missions, and remaining time for the current hunt"""
        await interaction.send(embed=archon_hunt(self.worldstate_url))
    
    @nextcord.slash_command()
    async def baro(self, interaction: nextcord.Interaction):
        """Get information on Baro Ki'Teer"""
        await interaction.send(embed=baro_kiteer(self.worldstate_url))

    @nextcord.slash_command()
    async def duviri(self, interaction: nextcord.Interaction):
        """Find information on the current Duviri cycle"""
        await interaction.send(embed=duviri_status(self.worldstate_url))
    
    @nextcord.slash_command()
    async def progenitors(self, interaction: nextcord.Interaction):
        """Returns progenitor elements and their corresponding warframes"""
        # Create the initial embed
        progenitor_embed = nextcord.Embed(
            title = "Progenitor Elements",
            color = nextcord.Colour.from_rgb(0, 128, 255)
        )
        # Unpack progenitor dictionary values
        impact_progenitors = ', '.join(self.progenitor['Impact'])
        heat_progenitors = ', '.join(self.progenitor['Heat'])
        cold_progenitors = ', '.join(self.progenitor['Cold'])
        electricity_progenitors = ', '.join(self.progenitor['Electricity'])
        toxin_progenitors = ', '.join(self.progenitor['Toxin'])
        magnetic_progenitors = ', '.join(self.progenitor['Magnetic'])
        radiation_progenitors = ', '.join(self.progenitor['Radiation'])
        # Add fields for each element and corresponding warframes
        progenitor_embed.add_field(name="Impact", value=f"{impact_progenitors}", inline=True)
        progenitor_embed.add_field(name="Heat", value=f"{heat_progenitors}", inline=True)
        progenitor_embed.add_field(name="Cold", value=f"{cold_progenitors}", inline=True)
        progenitor_embed.add_field(name="Electricity", value=f"{electricity_progenitors}", inline=True)
        progenitor_embed.add_field(name="Toxin", value=f"{toxin_progenitors}", inline=True)
        progenitor_embed.add_field(name="Magnetic", value=f"{magnetic_progenitors}", inline=True)
        progenitor_embed.add_field(name="Radiation", value=f"{radiation_progenitors}", inline=True)

        await interaction.send(embed=progenitor_embed)
    
    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def set_warframe_channel(self, interaction: nextcord.Interaction, channel: str):
        """Takes in a channel link/ID and sets it as the automated Warframe channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        wf_channel_id = int(channel.split("/")[-1])
        # Prepares the new guild & channel combination for this server
        new_channel = {"guild": interaction.guild_id, "channel": wf_channel_id}
        # Updates the Warframe channel for the server or inserts it if one doesn't exist currently
        db.warframe_channels.replace_one({"guild": interaction.guild_id}, new_channel, upsert=True)

        # Let users know where the updated channel is
        updated_channel = interaction.guild.get_channel(interaction.channel_id)
        if updated_channel:
            await interaction.send(f"Warframe content for this server will go to {updated_channel.name}.")
    
    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def remove_warframe_channel(self, interaction: nextcord.Interaction):
        """Removes the automated Warframe channel for this server, if it exists."""

        # Removes the Warframe channel for the server if it exists
        if db.warframe_channels.find_one({"guild": interaction.guild_id}):
            db.warframe_channels.delete_one({"guild": interaction.guild_id})
            await interaction.send("Warframe automated content for this server is stopped.")
        # Lets the user know if there is no existing Warframe channel
        else:
            await interaction.send("There is no Warframe automated content for this server.")

def setup(bot):
    bot.add_cog(Warframe(bot))