import nextcord
from os import getenv
from pymongo import MongoClient
from nextcord.ext import application_checks, commands, tasks
from requests import get, exceptions
from json import loads
from datetime import datetime, time
from re import sub

client = MongoClient(getenv("CONN_STRING"))
db = client.NextcordBot
worldstate_url = "https://api.warframe.com/cdn/worldState.php"


# Function to convert an epoch timestamp into a dynamic timestamp
def epoch_convert(epoch: str):
    epoch_num = epoch[:10]
    formatted_time = f"<t:{epoch_num}:f>"
    return formatted_time


# Function to put spaces before capitals in strings
def string_split(string: str):
    return sub(r"(?<!^)(?=[A-Z])", " ", string)


# Function to perform a GET request on Warframe's worldstate URL
def request_wf_info(url: str):
    try:
        # Return the parsed JSON as a Python object
        wf_data = get(url)
        wf_world = loads(wf_data.content)
        return wf_world
    except exceptions.RequestException as error:
        return error


# Function to get information on current alerts
def alerts_search(url: str):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about alerts
    alert_data = wf_world["Alerts"]

    # Create an embed object to return with alert information
    alert_embed = nextcord.Embed(
        title="Alerts", description="", color=nextcord.Colour.from_rgb(0, 128, 255)
    )

    for alert in alert_data:
        # Get the start and end times as dynamic timestamps
        alert_start = epoch_convert(alert["Activation"]["$date"]["$numberLong"])
        alert_end = epoch_convert(alert["Expiry"]["$date"]["$numberLong"])

        # Get information on the alert location, type, faction, and difficulty
        alert_mission = alert["MissionInfo"]
        alert_location = db.worldstate.find_one({"key": alert_mission["location"]})[
            "value"
        ]
        alert_type = db.worldstate.find_one({"key": alert_mission["missionType"]})[
            "value"
        ]
        alert_faction = db.worldstate.find_one({"key": alert_mission["faction"]})[
            "value"
        ]
        alert_min_level = alert_mission["minEnemyLevel"]
        alert_max_level = alert_mission["maxEnemyLevel"]
        alert_tag = (
            "Gift of the Lotus" if alert["Tag"] == "LotusGift" else "Tactical Alert"
        )

        # Get information on the alert rewards
        alert_reward = alert_mission["missionReward"]
        alert_credits = alert_reward["credits"]
        alert_items = alert_reward["countedItems"]

        # Get the alert tag and when it will be around
        alert_title = f"**{alert_tag}** from {alert_start} to {alert_end}\n"

        # Get the enemy level, faction, alert type and location
        alert_desc = f"Level {alert_min_level}-{alert_max_level} {alert_faction} {alert_type} on {alert_location}\n"

        # Append information about the alert
        alert_embed.add_field(name=alert_title, value=alert_desc)

        # Append the alert credit reward
        alert_rewards = f"- {alert_credits} credits\n"

        # Get the type and quantity of additional rewards
        for item in alert_items:
            try:
                item_type = db.languages.find_one({"key": item["ItemType"]})["value"]
            except:
                item_type = item["ItemType"].split("/")[-1]
            item_count = item["ItemCount"]
            alert_rewards += f"- {item_count} {item_type}\n"

        alert_embed.add_field(name="Rewards:", value=alert_rewards, inline=False)

    return alert_embed


# Function to get information on this week's archon hunt
def archon_hunt(url: str):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about Archon Hunts
    archon_info = wf_world["LiteSorties"][0]

    # Convert the Archon's arrival and expiry as dynamic timestamps
    archon_start = epoch_convert(archon_info["Activation"]["$date"]["$numberLong"])
    archon_end = epoch_convert(archon_info["Expiry"]["$date"]["$numberLong"])
    archon_duration = f"{archon_start} - {archon_end}"

    # Get the current Archon and the missions leading up to them
    current_archon = db.worldstate.find_one({"key": archon_info["Boss"]})["value"]
    archon_missions = archon_info["Missions"]

    hunt_info = []
    # Append each mission type and node
    for mission in archon_missions:
        mission_type = db.worldstate.find_one({"key": mission["missionType"]})["value"]
        mission_node = db.worldstate.find_one({"key": mission["node"]})["value"]
        hunt_info.append(f"{mission_type} - {mission_node}")

    # Create an embed object to return with Archon information
    archon_embed = nextcord.Embed(
        title=f"{current_archon}",
        description="\n".join(hunt_info),
        color=nextcord.Colour.from_rgb(0, 128, 255),
    )

    archon_embed.add_field(name="Archon is here from:", value=archon_duration)
    return archon_embed


# Function to handle retrieving when Baro Ki'Teer will arrive or if he is here currently
def baro_kiteer(url: str):
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
            title="Baro Ki'Teer has not arrived yet",
            description="Inventory Unknown",
            color=nextcord.Colour.from_rgb(0, 128, 255),
        )
        return baro_embed

    # Get the start and end times as dynamic timestamps
    baro_start = epoch_convert(baro["Activation"]["$date"]["$numberLong"])
    baro_end = epoch_convert(baro["Expiry"]["$date"]["$numberLong"])
    baro_duration = f"{baro_start} - {baro_end}"

    # Get Baro's location
    baro_location = db.worldstate.find_one({"key": baro["Node"]})["value"]

    # Create an embed object to return with Baro information
    baro_embed = nextcord.Embed(
        title="Baro Ki'Teer is here",
        description=baro_location,
        color=nextcord.Colour.from_rgb(0, 128, 255),
    )

    # Iterate Baro's inventory
    for item in baro_inventory:
        # Get each item's name, ducat, and credit cost
        ducats = item["PrimePrice"]
        credits = item["RegularPrice"]

        # Check if the item is in the dictionary in both regular and lowercase
        if db.languages.find_one({"key": item["ItemType"]}):
            name = db.languages.find_one({"key": item["ItemType"]})["value"]
        elif db.languages.find_one({"key": item["ItemType"].lower()}):
            name = db.languages.find_one({"key": item["ItemType"].lower()})["value"]
        # Otherwise take the item name as shown
        else:
            name = item["ItemType"].split("/")[-1]

        # Format everything into one line and append it to the embed
        baro_embed.add_field(f"{name} - {ducats} D - {credits} C")

    baro_embed.add_field(name="Baro is here from:", value=baro_duration)
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
        title="Weekly Duviri Rewards",
        description="This week's rewards in the Circuit",
        color=nextcord.Colour.from_rgb(0, 128, 255),
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
        name="**Circuit Rewards** (Choose one)", value=duviri_regular
    )
    duviri_embed.add_field(
        name="**Steel Path Circuit Rewards** (Choose one)", value=duviri_steel_path
    )

    return duviri_embed


# Function to get information on Nightwave
def nightwave_status(url: str):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about Nightwave
    nw = wf_world["SeasonInfo"]

    # Get the start and end time for the Nightwave Season as dynamic timestamps
    nw_start = epoch_convert(nw["Activation"]["$date"]["$numberLong"])
    nw_end = epoch_convert(nw["Expiry"]["$date"]["$numberLong"])
    nw_duration = f"{nw_start} - {nw_end}"

    # Get the current Nightwave season
    nw_season = nw["Season"]

    # Get the current Nightwave challenges
    nw_challenges = nw["ActiveChallenges"]

    # Create a string with the current Nightwave season
    nw_title = f"**Nightwave Season {nw_season}**"

    # Create an embed object to return with Duviri information
    nw_embed = nextcord.Embed(
        title=nw_title,
        description=nw_duration,
        color=nextcord.Colour.from_rgb(0, 128, 255),
    )

    challenge_info = ""

    for challenge in nw_challenges:
        # Get whether the challenge is daily or weekly
        try:
            if challenge["Daily"]:
                duration = "Daily"
        except:
            duration = "Weekly"

        # Get the start and end time for the challenge
        start = epoch_convert(challenge["Activation"]["$date"]["$numberLong"])
        end = epoch_convert(challenge["Expiry"]["$date"]["$numberLong"])

        # Get the requirement for the challenge
        if db.languages.find_one({"key": challenge["Challenge"]}):
            requirement_match = db.languages.find_one({"key": challenge["Challenge"]})
            requirement_name = requirement_match["value"]
            requirement_desc = requirement_match["desc"]
            requirement = f"{requirement_name} - {requirement_desc}"
        elif db.languages.find_one({"key": challenge["Challenge"].lower()}):
            requirement_match = db.languages.find_one(
                {"key": challenge["Challenge"].lower()}
            )
            requirement_name = requirement_match["value"]
            requirement_desc = requirement_match["desc"]
            requirement = f"{requirement_name} - {requirement_desc}"
        else:
            requirement = challenge["Challenge"].split("/")[-1]

        challenge_info += f"- ({duration}) {requirement} {start}-{end}\n"

    nw_embed.add_field(name="Rewards:", value=challenge_info)

    return nw_embed


# Function to get information on the current sortie
def sortie_status(url: str):
    # Convert the response content for the world state into a Python object
    wf_world = request_wf_info(url)

    # Access specifically the information about sorties
    sorties = wf_world["Sorties"][0]

    # Get the start and end time for sorties as a dynamic timestamp
    sortie_start = epoch_convert(sorties["Activation"]["$date"]["$numberLong"])
    sortie_end = epoch_convert(sorties["Expiry"]["$date"]["$numberLong"])

    # Get the sortie boss and missions
    sortie_boss = db.worldstate.find_one({"key": sorties["Boss"]})["value"]
    missions = sorties["Variants"]

    # Create the message for when the sortie will be around
    sortie_title = f"**Sortie** {sortie_boss} from {sortie_start} to {sortie_end}\n"
    sortie_missions = ""

    # Get each missions type, modifier, and node
    for mission in missions:
        sortie_type = db.worldstate.find_one({"key": mission["missionType"]})["value"]
        sortie_modifier = db.worldstate.find_one({"key": mission["modifierType"]})[
            "value"
        ]
        sortie_node = db.worldstate.find_one({"key": mission["node"]})["value"]
        sortie_missions += f"{sortie_type} {sortie_node} {sortie_modifier}\n"

    # Create an embed object to return with sortie information
    sortie_embed = nextcord.Embed(
        title=sortie_title,
        description=sortie_missions,
        color=nextcord.Colour.from_rgb(0, 128, 255),
    )

    return sortie_embed


class Warframe(commands.Cog, name="Warframe"):
    """Commands for getting Warframe information"""

    COG_EMOJI = "⚔️"

    def __init__(self, bot):
        self.bot = bot
        # Create a dictionary of Warframe Progenitor types to retrieve later
        self.progenitor = {
            "Impact": [
                "Baruuk",
                "Dante",
                "Gauss",
                "Grendel",
                "Rhino",
                "Sevagoth",
                "Wukong",
                "Zephyr",
            ],
            "Heat": [
                "Chroma",
                "Ember",
                "Inaros",
                "Jade",
                "Kullervo",
                "Nezha",
                "Protea",
                "Temple",
                "Vauban",
                "Wisp",
            ],
            "Cold": [
                "Frost",
                "Gara",
                "Hildryn",
                "Koumei",
                "Revenant",
                "Styanax",
                "Titania",
                "Trinity",
            ],
            "Electricity": [
                "Banshee",
                "Caliban",
                "Excalibur",
                "Gyre",
                "Limbo",
                "Nova",
                "Valkyr",
                "Volt",
            ],
            "Toxin": [
                "Atlas",
                "Dagath",
                "Ivara",
                "Khora",
                "Nekros",
                "Nidus",
                "Nokko",
                "Oberon",
                "Oraxia",
                "Saryn",
            ],
            "Magnetic": [
                "Citrine",
                "Cyte-09",
                "Harrow",
                "Hydroid",
                "Lavos",
                "Mag",
                "Mesa",
                "Xaku",
                "Yareli",
            ],
            "Radiation": [
                "Ash",
                "Equinox",
                "Garuda",
                "Loki",
                "Mirage",
                "Nyx",
                "Octavia",
                "Qorvex",
                "Voruna",
            ],
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
    @tasks.loop(time=time(15))
    async def baro_timer(self):
        # Checks every day at 14:00 UTC / 9:00 am EST for Baro Ki'Teer
        weekday = datetime.today().weekday()
        # If date is Friday, then run the Baro function
        if weekday == 4:
            # Fetch the list of enrolled warframe channels to post daily content to
            self.daily_wf_channels = db.warframe_channels.distinct("channel")
            # Send the content to each of the daily warframe channels
            for channel_id in self.daily_wf_channels:
                daily_wf_channel = self.bot.get_channel(channel_id)
                if daily_wf_channel is None:
                    daily_wf_channel = await self.bot.fetch_channel(channel_id)
                await daily_wf_channel.send(embed=baro_kiteer(self.worldstate_url))

    # Archon loop runs every Sunday for the weekly reset
    @tasks.loop(time=time(2))
    async def archon_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for Archon Hunts
        weekday = datetime.today().weekday()
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
    @tasks.loop(time=time(2))
    async def duviri_timer(self):
        # Checks every day at 2:00 am UTC / 9:00 pm EST for Duviri Rewards
        weekday = datetime.today().weekday()
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
    async def alerts(self, interaction: nextcord.Interaction):
        """Find information on current alerts, if there are any"""
        await interaction.send(embed=alerts_search(self.worldstate_url))

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
        """Find information on the current Duviri cycle rewards"""
        await interaction.send(embed=duviri_status(self.worldstate_url))

    @nextcord.slash_command()
    async def nightwave(self, interaction: nextcord.Interaction):
        """Find information on the current Nightwave season and challenges"""
        await interaction.send(embed=nightwave_status(self.worldstate_url))

    @nextcord.slash_command()
    async def sortie(self, interaction: nextcord.Interaction):
        """Find information on the current sortie"""
        await interaction.send(embed=sortie_status(self.worldstate_url))

    @nextcord.slash_command()
    async def progenitors(self, interaction: nextcord.Interaction):
        """Returns progenitor elements and their corresponding warframes"""
        # Create the initial embed
        progenitor_embed = nextcord.Embed(
            title="Progenitor Elements", color=nextcord.Colour.from_rgb(0, 128, 255)
        )
        # Add fields for each element and corresponding warframes
        for key in self.progenitor:
            progenitors = ", ".join(self.progenitor[key])
            progenitor_embed.add_field(name=key, value=progenitors)

        await interaction.send(embed=progenitor_embed)

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def set_warframe_channel(
        self, interaction: nextcord.Interaction, channel: str
    ):
        """Takes in a channel link/ID and sets it as the automated Warframe channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        wf_channel_id = int(channel.split("/")[-1])
        # Prepares the new guild & channel combination for this server
        new_channel = {"guild": interaction.guild_id, "channel": wf_channel_id}
        # Updates the Warframe channel for the server or inserts it if one doesn't exist currently
        db.warframe_channels.replace_one(
            {"guild": interaction.guild_id}, new_channel, upsert=True
        )

        # Let users know where the updated channel is
        updated_channel = interaction.guild.get_channel(interaction.channel_id)
        if updated_channel:
            await interaction.send(
                f"Warframe content for this server will go to {updated_channel.name}."
            )

    @nextcord.slash_command()
    @application_checks.has_permissions(manage_guild=True)
    async def remove_warframe_channel(self, interaction: nextcord.Interaction):
        """Removes the automated Warframe channel for this server, if it exists."""

        # Removes the Warframe channel for the server if it exists
        if db.warframe_channels.find_one({"guild": interaction.guild_id}):
            db.warframe_channels.delete_one({"guild": interaction.guild_id})
            await interaction.send(
                "Warframe automated content for this server is stopped."
            )
        # Lets the user know if there is no existing Warframe channel
        else:
            await interaction.send(
                "There is no Warframe automated content for this server."
            )


def setup(bot):
    bot.add_cog(Warframe(bot))
