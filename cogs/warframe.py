import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import commands
import requests
import json


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
    
    # Create a dictionary storing the info we need to return that we can unpack later
    archon_hunt_info = {
        "archon": archon,
        "remaining_time": remaining_time,
        "nodes": nodes
    }
    return archon_hunt_info

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

    # Create a dictionary storing the info we need to return that we can unpack later
    void_trader_info = {
        "location": baro_location,
        "time": baro_arrival,
        "inventory": baro_inventory
    }
    return void_trader_info

# Function to handle the retrieval of Duviri information
def duviri_status(url):
    # Try to get Duviri information from the API and handle errors
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

    # Create a dictionary storing the info we need to return that we can unpack later
    duviri_info = {
        "emotion": str.capitalize(emotion),
        "regular": regular_rewards,
        "steel_path": steel_path_rewards
    }
    return duviri_info

def open_worlds(url):
    # Try to get the weekly Teshin Reward information and handle errors
    try:
        wf_data = requests.get(url)
    except requests.exceptions.RequestException as error:
        return error
    # Convert the response content for the Teshin Reward into a Python object
    wf_content = json.loads(wf_data.content)
    # Parse the object for open world state and time for the plains, vallis, and cambion areas
    plains_status = wf_content['cetusCycle']
    plains_state = plains_status['state']
    plains_time = plains_status['timeLeft']
    vallis_status = wf_content['vallisCycle']
    vallis_state = vallis_status['state']
    vallis_time = vallis_status['timeLeft']
    cambion_status = wf_content['cambionCycle']
    cambion_state = cambion_status['state']
    cambion_time = cambion_status['timeLeft']

    # Create a dictionary storing the info we need to return that we can unpack later
    open_worlds_info = {
        "plains_state": str.capitalize(plains_state),
        "plains_time": plains_time,
        "vallis_state": str.capitalize(vallis_state),
        "vallis_time": vallis_time,
        "cambion_state": str.capitalize(cambion_state),
        "cambion_time": cambion_time,
    }
    return open_worlds_info   

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

    # Create a dictionary storing the info we need to return that we can unpack later
    teshin_reward_info = {
        "reward_name": reward_name,
        "reward_cost": reward_cost,
        "remaining_time": remaining_time
    }
    return teshin_reward_info

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

    @nextcord.slash_command()
    async def archon(self, interaction: nextcord.Interaction):
        """Find the current Archon, missions, and remaining time for the current hunt"""
        archon_hunt_info = archon_hunt(self.warframe_api)
        archon_expiry = "-".join(archon_hunt_info["remaining_time"])
        embed = nextcord.Embed(
            title = archon_hunt_info["archon"], 
            description = "\n".join(archon_hunt_info["nodes"]),
            color = nextcord.Colour.from_rgb(0, 128, 255)
            )
        embed.set_footer(archon_expiry)
        await interaction.send(embed=embed)
    
    @nextcord.slash_command()
    async def baro(self, interaction: nextcord.Interaction):
        """Get information on Baro Ki'Teer"""
        baro_kiteer_info = baro_kiteer(self.warframe_api)
        baro_location = baro_kiteer_info["location"]
        baro_time = " ".join(baro_kiteer_info["time"])
        baro_inventory = baro_kiteer_info['inventory']
        embed = nextcord.Embed(
            title = f"Baro Ki'Teer will arrive at {baro_location} in {baro_time}",
            description = "\n".join(baro_inventory) if baro_inventory else "Inventory Unknown",
            color = nextcord.Colour.from_rgb(0, 128, 255)
        )
        await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def duviri(self, interaction: nextcord.Interaction):
        """Find information on the current Duviri cycle"""
        duviri_info = duviri_status(self.warframe_api)
        duviri_regular = "\n".join(duviri_info["regular"])
        duviri_steel_path = "\n".join(duviri_info["steel_path"])
        embed = nextcord.Embed(
            title = "Duviri Status",
            description = f'Current Cycle: {duviri_info["emotion"]}',
            color = nextcord.Colour.from_rgb(0, 128, 255)
        )
        embed.add_field(name="Regular Rewards", value=duviri_regular, inline=False)
        embed.add_field(name="Steel Path Rewards", value=duviri_steel_path, inline=False)
        await interaction.send(embed=embed)
    
    @nextcord.slash_command()
    async def open_worlds(self, interaction: nextcord.Interaction):
        """Find information on the status of open world locations"""
        open_world_info = open_worlds(self.warframe_api)
        embed = nextcord.Embed(
            title = "Open World Status",
            color = nextcord.Colour.from_rgb(0, 128, 255)
        )
        embed.add_field(
            name = "Plains of Eidolon", 
            value = f'{open_world_info["plains_state"]} - {open_world_info["plains_time"]}',
            inline = False
        )
        embed.add_field(
            name = "Orb Vallis", 
            value = f'{open_world_info["vallis_state"]} - {open_world_info["vallis_time"]}',
            inline = False
        )
        embed.add_field(
            name = "Cambion Drift", 
            value = f'{open_world_info["cambion_state"]} - {open_world_info["cambion_time"]}',
            inline = False
        )
        await interaction.send(embed=embed)
    
    @nextcord.slash_command()
    async def steel_path_reward(self, interaction: nextcord.Interaction):
        """Finds the weekly reward from Teshin"""
        teshin_info = teshin_rotation(self.warframe_api)
        teshin_time = f"Expires in {" ".join(teshin_info["remaining_time"])}"
        embed = nextcord.Embed(
            title = f"Teshin Weekly Reward:",
            description = f'{teshin_info["reward_name"]} for {teshin_info["reward_cost"]} Steel Essence'
        )
        embed.set_footer(teshin_time)
        await interaction.send(embed=embed)

def setup(bot):
    bot.add_cog(Warframe(bot))