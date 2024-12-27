import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import commands, tasks
import requests
import json
import datetime

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot 

daily_channel_id = 1228495611498594304

def archon_hunt(url):
    # Try to get the weekly Archon Hunt information and handle errors
    try:
        wf_data = requests.get(url)
    except requests.exceptions.RequestException as error:
        return error
    # Convert the response content for the Archon Hunt into a Python object
    archon_hunt = json.loads(wf_data.content)['archonHunt']
    # Parse the object for the current Archon Hunt target, missions, and remaining time
    archon = archon_hunt['boss']
    missions = archon_hunt['missions'][0:3]
    remaining_time = archon_hunt['eta'].split(" ")[0:2]
    # Parse the node and mission type for each missions
    nodes = []
    for mission in missions:
        nodes.append(f"{mission['node']} - {mission['type']}")

    # Create an embed object to return with Archon information
    archon_expiry = " ".join(remaining_time)
    archon_embed = nextcord.Embed(
        title = archon, 
        description = "\n".join(nodes),
        color = nextcord.Colour.from_rgb(0, 128, 255)
        )
    archon_embed.add_field(name="Expires in:", value=archon_expiry, inline=True)
    return archon_embed

# Function to handle retrieving when Baro Ki'Teer will arrive or if he is here currently
def baro_kiteer(url):
    # Try to get the time to Baro's arrival and handle errors
    try:
        wf_data = requests.get(url)
    except requests.exceptions.RequestException as error:
        return error
    # Convert the response content for the Void Trader into a Python object
    baro_info = json.loads(wf_data.content)['voidTrader']
    # Parse the object for the next Void trader location, arrival time (days and hours), and 
    baro_location = baro_info['location']
    baro_arrival = baro_info['startString'].split(" ")[0:2]
    baro_inventory = baro_info['inventory']

    # Create an embed object to return with Baro information
    baro_time = " ".join(baro_arrival)
    baro_items = ""
    for item in baro_inventory:
        baro_items += (f"{item['item']} - {item['ducats']} Ducats - {item['credits']} Credits\n")
    baro_embed = nextcord.Embed(
        title = f"Baro Ki'Teer will arrive at {baro_location} in {baro_time}",
        description = baro_items if baro_inventory else "Inventory Unknown",
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )
    return baro_embed

# Function to handle the retrieval of Duviri information
def duviri_status(url):
    # Try to get Duviri information and handle errors
    try:
        wf_data = requests.get(url)
    except requests.exceptions.RequestException as error:
        return error
    # Convert the response content for the Duviri Cycle into a Python object
    duviri = json.loads(wf_data.content)['duviriCycle']
    # Parse the object for Duviri emotion, regular rewards and Steel Path rewards
    emotion = duviri['state']
    regular_rewards = duviri['choices'][0]['choices']
    steel_path_rewards = duviri['choices'][1]['choices']

    # Create an embed object to return with Duviri information
    duviri_regular = "\n".join(regular_rewards)
    duviri_steel_path = "\n".join(steel_path_rewards)
    duviri_embed = nextcord.Embed(
        title = "Duviri Status",
        description = f'Current Cycle: {str.capitalize(emotion)}',
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )
    duviri_embed.add_field(name="Regular Rewards", value=duviri_regular, inline=False)
    duviri_embed.add_field(name="Steel Path Rewards", value=duviri_steel_path, inline=False)
    return duviri_embed

def open_worlds(url):
    # Try to get the current Open World information and handle errors
    try:
        wf_data = requests.get(url)
    except requests.exceptions.RequestException as error:
        return error
    # Convert the response content for the Teshin Reward into a Python object
    wf_content = json.loads(wf_data.content)
    # Parse the object for open world state and time for the plains, vallis, and cambion areas
    plains_status = wf_content['cetusCycle']
    plains_state = str.capitalize(plains_status['state'])
    plains_time = plains_status['timeLeft']
    vallis_status = wf_content['vallisCycle']
    vallis_state = str.capitalize(vallis_status['state'])
    vallis_time = vallis_status['timeLeft']
    cambion_status = wf_content['cambionCycle']
    cambion_state = str.capitalize(cambion_status['state'])
    cambion_time = cambion_status['timeLeft']

    # Create an embed object to return with Open World information
    open_world_embed = nextcord.Embed(
        title = "Open World Status",
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )
    open_world_embed.add_field(
        name = "Plains of Eidolon", 
        value = f'{plains_state} - {plains_time}',
        inline = False
    )
    open_world_embed.add_field(
        name = "Orb Vallis", 
        value = f'{vallis_state} - {vallis_time}',
        inline = False
    )
    open_world_embed.add_field(
        name = "Cambion Drift", 
        value = f'{cambion_state} - {cambion_time}',
        inline = False
    )
    return open_world_embed   

def teshin_rotation(url):
    # Try to get the weekly Teshin Reward information and handle errors
    try:
        wf_data = requests.get(url)
    except requests.exceptions.RequestException as error:
        return error
    # Convert the response content for the Teshin Reward into a Python object
    current_reward = json.loads(wf_data.content)['steelPath']
    # Parse the object for the current reward name and cost
    reward_name = current_reward['currentReward']['name']
    reward_cost = current_reward['currentReward']['cost']
    remaining_time = current_reward['remaining'].split(" ")[0:2]

    # Create an embed object to return with Teshin information
    teshin_time = " ".join(remaining_time)
    teshin_embed = nextcord.Embed(
        title = f"Teshin Weekly Reward:",
        description = f'{reward_name} for {reward_cost} Steel Essence',
        color = nextcord.Colour.from_rgb(0, 128, 255)
    )
    teshin_embed.add_field(name="Expires in:", value=teshin_time, inline=True)
    return teshin_embed

class Warframe(commands.Cog, name="Warframe"):
    """Commands for getting Warframe information"""

    COG_EMOJI = "⚔️"

    def __init__(self, bot):
        self.bot = bot
        # Create a dictionary of Warframe Progenitor types to retrieve later
        self.progenitors = {
            "Impact": ["Baruuk", "Dante", "Gauss", "Grendel", "Rhino", "Sevagoth", "Wukong", "Zephyr"],
            "Heat": ["Chroma", "Ember", "Inaros", "Jade", "Kullervo", "Nezha", "Protea", "Vauban", "Wisp"],
            "Cold": ["Frost", "Gara", "Hildryn", "Koumei", "Revenant", "Styanax", "Titania", "Trinity"],
            "Electricity": ["Banshee", "Caliban", "Excalibur", "Gyre", "Limbo", "Nova", "Valkyr", "Volt"],
            "Toxin": ["Atlas", "Dagath", "Ivara", "Khora", "Nekros", "Nidus", "Oberon", "Saryn"],
            "Magnetic": ["Citrine", "Cyte-09", "Harrow", "Hydroid", "Lavos", "Mag", "Mesa", "Xaku", "Yareli"],
            "Radiation": ["Ash", "Equinox", "Garuda", "Loki", "Mirage", "Nyx", "Octavia", "Qorvex", "Voruna"]
        }
        self.warframe_api = "https://api.warframestat.us/pc"
        self.archon_timer.start()
        self.baro_timer.start()
        self.duviri_timer.start()
        self.teshin_timer.start()

    def cog_unload(self):
        self.archon_timer.cancel()
        self.baro_timer.cancel()
        self.duviri_timer.cancel()
        self.teshin_timer.cancel()

    # Baro loop runs every Friday to check if Baro has arrived
    @tasks.loop(time=datetime.time(15))
    async def baro_timer(self):
        # Checks every day at 14:00 UTC / 9:00 am EST for Baro Ki'Teer
        weekday = datetime.datetime.today().weekday()
        # If date is Friday, then run the Baro function
        if weekday is 4:
            daily_channel = self.bot.get_channel(daily_channel_id)
            if daily_channel is None:
                daily_channel = await self.bot.fetch_channel(daily_channel_id)
            await daily_channel.send(embed=baro_kiteer(self.warframe_api))

    # Archon loop runs every Sunday for the weekly reset
    @tasks.loop(time=datetime.time(2))
    async def archon_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for Archon Hunts
        weekday = datetime.datetime.today().weekday()
        # If date is Sunday(EST)/Monday(UTC), then run the Archon Hunt function
        if weekday is 0:
            daily_channel = self.bot.get_channel(daily_channel_id)
            if daily_channel is None:
                daily_channel = await self.bot.fetch_channel(daily_channel_id)
            await daily_channel.send(embed=archon_hunt(self.warframe_api))

    # Duviri loop runs every Sunday for the weekly reset
    @tasks.loop(time=datetime.time(2))
    async def duviri_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for Duviri Rewards
        weekday = datetime.datetime.today().weekday()
        # If date is Sunday(EST)/Monday(UTC), then run the Duviri rewards function
        if weekday is 0:
            daily_channel = self.bot.get_channel(daily_channel_id)
            if daily_channel is None:
                daily_channel = await self.bot.fetch_channel(daily_channel_id)
            await daily_channel.send(embed=duviri_status(self.warframe_api))

    # Teshin loop runs every Sunday for the weekly reset
    @tasks.loop(time=datetime.time(2))
    async def teshin_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for the Teshin weekly reward
        weekday = datetime.datetime.today().weekday()
        # If date is Sunday(EST)/Monday(UTC), then run the Teshin reward function
        if weekday is 0:
            daily_channel = self.bot.get_channel(daily_channel_id)
            if daily_channel is None:
                daily_channel = await self.bot.fetch_channel(daily_channel_id)
            await daily_channel.send(embed=teshin_rotation(self.warframe_api))

    @nextcord.slash_command()
    async def archon(self, interaction: nextcord.Interaction):
        """Find the current Archon, missions, and remaining time for the current hunt"""
        await interaction.send(embed=archon_hunt(self.warframe_api))
    
    @nextcord.slash_command()
    async def baro(self, interaction: nextcord.Interaction):
        """Get information on Baro Ki'Teer"""
        await interaction.send(embed=baro_kiteer(self.warframe_api))

    @nextcord.slash_command()
    async def duviri(self, interaction: nextcord.Interaction):
        """Find information on the current Duviri cycle"""
        await interaction.send(embed=duviri_status(self.warframe_api))
    
    @nextcord.slash_command()
    async def open_worlds(self, interaction: nextcord.Interaction):
        """Find information on the status of open world locations"""
        await interaction.send(embed=open_worlds(self.warframe_api))
    
    @nextcord.slash_command()
    async def progenitors(self, interaction: nextcord.Interaction):
        """Returns progenitor elements and their corresponding warframes"""
        # Create the initial embed
        progenitor_embed = nextcord.Embed(
            title = "Progenitor Elements",
            color = nextcord.Colour.from_rgb(0, 128, 255)
        )
        # Add fields for each element and corresponding warframes
        progenitor_embed.add_field(name="Impact", value=f"{self.progenitors['Impact']}", inline=True)
        progenitor_embed.add_field(name="Heat", value=f"{self.progenitors['Heat']}", inline=True)
        progenitor_embed.add_field(name="Cold", value=f"{self.progenitors['Cold']}", inline=True)
        progenitor_embed.add_field(name="Electricity", value=f"{self.progenitors['Electricity']}", inline=True)
        progenitor_embed.add_field(name="Toxin", value=f"{self.progenitors['Toxin']}", inline=True)
        progenitor_embed.add_field(name="Magnetic", value=f"{self.progenitors['Magnetic']}", inline=True)
        progenitor_embed.add_field(name="Radiation", value=f"{self.progenitors['Radiation']}", inline=True)

        await interaction.send(embed=progenitor_embed)
    
    @nextcord.slash_command()
    async def steel_path_reward(self, interaction: nextcord.Interaction):
        """Finds the weekly reward from Teshin"""
        await interaction.send(embed=teshin_rotation(self.warframe_api))

def setup(bot):
    bot.add_cog(Warframe(bot))