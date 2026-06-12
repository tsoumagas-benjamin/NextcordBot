import stoat
from stoat.ext import commands
from re import sub
from utilities import ChaosBot, db, delay_until, schedule, time_from_string
import asyncio

# TODO: Switch from MongoDB


# Function to convert an epoch timestamp into a dynamic timestamp
def epoch_convert(epoch: str):
    epoch_num = epoch[:10]
    formatted_time = f"<t:{epoch_num}:f>"
    return formatted_time


# Function to put spaces before capitals in strings
def string_split(string: str):
    return sub(r"(?<!^)(?=[A-Z])", " ", string)


# Function to perform a GET request on Warframe's worldstate URL
async def request_wf_info(bot: ChaosBot, url: str):
    try:
        # Return the parsed JSON as a Python object
        wf_world = await bot.client.get_content(url)
        return wf_world
    except Exception as error:
        return error


# Function to get information on current alerts
async def alerts_search(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

    # Access specifically the information about alerts
    alert_data = wf_world["Alerts"]

    # Store all the alert information to pass to the embed
    alert_info = ""

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
        alert_info += f"**{alert_title}**\t- {alert_desc}"

        # Append the alert credit reward
        alert_rewards = f"- {alert_credits} credits\n"

        # Get the type and quantity of additional rewards
        for item in alert_items:
            try:
                item_type = db.languages.find_one({"key": item["ItemType"]})["value"]
            except Exception:
                item_type = item["ItemType"].split("/")[-1]
            item_count = item["ItemCount"]
            alert_rewards += f"- {item_count} {item_type}\n"

        alert_info += f"**Rewards:**\n{alert_rewards}"

    # Create an embed object to return with alert information
    alert_embed = stoat.SendableEmbed(
        title="Alerts", description=alert_info, color=stoat.Colour.from_rgb(0, 128, 255)
    )

    return alert_embed


# Function to get information on this week's archon hunt
async def archon_hunt(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

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
    archon_embed = stoat.SendableEmbed(
        title=f"{current_archon} is here between {archon_duration}",
        description="\n".join(hunt_info),
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return archon_embed


# Function to handle retrieving when Baro Ki'Teer will arrive or if he is here currently
async def baro_kiteer(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

    # Access specifically the information about Baro Ki'Teer
    baro = wf_world["VoidTraders"][0]

    # Get the start and end times as dynamic timestamps
    baro_start = epoch_convert(baro["Activation"]["$date"]["$numberLong"])
    baro_end = epoch_convert(baro["Expiry"]["$date"]["$numberLong"])
    baro_duration = f"{baro_start} - {baro_end}"

    # Get Baro's location
    try:
        baro_location = db.worldstate.find_one({"key": baro["Node"]})["value"]
    except Exception:
        baro_location = "an unknown location"

    try:
        # Check if Baro has inventory/is available
        if baro["Manifest"]:
            baro_inventory = baro["Manifest"]
    except Exception:
        # Create an embed object to return with Baro information
        baro_embed = stoat.SendableEmbed(
            title=f"Baro Ki'Teer will be at {baro_location} between {baro_duration}",
            description="Inventory Unknown",
            color=stoat.Colour.from_rgb(0, 128, 255),
        )
        return baro_embed

    baro_list = []

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

        # Format everything into one line and append it to the list
        baro_list.append(f"{name} - {ducats} D {credits} C")

    # # Break Baro's inventory into chunks of 10 items to avoid going over Discord's limits per field
    # chunk_size = 10
    # baro_chunked = [
    #     baro_list[item : item + chunk_size]
    #     for item in range(0, len(baro_list), chunk_size)
    # ]

    # # Append each chunk's information to the embed
    # for chunk in baro_chunked:
    #     baro_embed.add_field(name="", value="\n".join(chunk), inline=False)

    # Create an embed object to return with Baro information
    baro_embed = stoat.SendableEmbed(
        title=f"Baro Ki'Teer is at {baro_location} between {baro_duration}",
        description=baro_list,
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return baro_embed


# Function to get information on the current Deep Archimedea
async def deep_archimedea_status(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

    # Access specifically the information about sorties
    da = wf_world["Conquests"][0]

    # Get the start and end times as dynamic timestamps
    da_start = epoch_convert(da["Activation"]["$date"]["$numberLong"])
    da_end = epoch_convert(da["Expiry"]["$date"]["$numberLong"])
    da_duration = f"{da_start} - {da_end}"

    # Get the Deep Archimedea missions
    da_missions = da["Missions"]

    # Store information on the deep archimedea
    da_description = ""

    # Get each mission's faction, type, and modifiers
    for mission in da_missions:
        # Add mission type and enemy faction to the embed
        da_faction = db.worldstate.find_one({"key": mission["faction"]})["value"]
        da_type = db.worldstate.find_one({"key": mission["missionType"]})["value"]
        da_description += f"**{da_type}** - {da_faction}\n"

        # Get modifiers for both regular and elite difficulties
        da_difficulties = mission["difficulties"]

        # Handle risks and deviations for normal difficulties
        da_normal = da_difficulties[0]
        normal_dev = string_split(da_normal["deviation"])
        da_description += f"Deviations {normal_dev}\n"

        normal_risks = da_normal["risks"]
        da_risks = []

        for risk in normal_risks:
            da_risks.append(f"  - {string_split(risk)}")

        da_description += f"Risks:{'\t'.join(da_risks)}\n"

        # Handle additional risks for elite difficulties
        da_elite = da_difficulties[1]

        elite_risks = da_elite["risks"]
        eda_risks = []

        for risk in elite_risks:
            eda_risks.append(f"  - {string_split(risk)}")

        da_description += f"Elite Risks:{'\t'.join(eda_risks)}\n"

        # Get Deep Archimedea variables
        da_variables = da["Variables"]
        parsed_variables = []

        for variable in da_variables:
            parsed_variables.append(f"  - {string_split(variable)}")

        da_description += f"Variables:{'\t'.join(parsed_variables)}"

    # Create the Deep Archimedea embed
    da_embed = stoat.SendableEmbed(
        title=f"Deep Archimedea {da_duration}",
        description=da_description,
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return da_embed


# Function to handle the retrieval of Duviri information
async def duviri_status(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

    # Access specifically the information about Duviri
    duviri = wf_world["EndlessXpChoices"]

    # Look in both regular and steel path variants for reward choices
    regular_choices = duviri[0]["Choices"]
    steel_path_choices = duviri[1]["Choices"]

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
    duviri_description = f"**Circuit Rewards** (Choose one)\n{duviri_regular}\n"
    duviri_description += (
        f"**Steel Path Circuit Rewards (Choose two)\n{duviri_steel_path}\n"
    )

    # Create an embed object to return with Duviri information
    duviri_embed = stoat.SendableEmbed(
        title="Weekly Duviri Rewards",
        description=duviri_description,
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return duviri_embed


# Function to get information on Nightwave
async def nightwave_status(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

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

    challenge_info = ""

    for challenge in nw_challenges:
        # Get whether the challenge is daily or weekly
        try:
            if challenge["Daily"]:
                duration = "Daily"
        except Exception:
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

    # Create an embed object to return with Duviri information
    nw_embed = stoat.SendableEmbed(
        title=f"{nw_title} - {nw_duration}",
        description=f"Rewards:\n{challenge_info}",
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return nw_embed


# Function to get information on the current sortie
async def sortie_status(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

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
    sortie_embed = stoat.SendableEmbed(
        title=sortie_title,
        description=sortie_missions,
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return sortie_embed


# Function to get information on the current Temporal Archimedea
async def temporal_archimedea_status(bot: ChaosBot, url: str):
    # Convert the response content for the world state into a Python object
    wf_world = await request_wf_info(bot, url)

    # Access specifically the information about sorties
    ta = wf_world["Conquests"][1]

    # Get the start and end times as dynamic timestamps
    ta_start = epoch_convert(ta["Activation"]["$date"]["$numberLong"])
    ta_end = epoch_convert(ta["Expiry"]["$date"]["$numberLong"])
    ta_duration = f"{ta_start} - {ta_end}"

    # Get the Deep Archimedea missions
    ta_missions = ta["Missions"]

    # Store information on the temporal archimedea
    ta_description = ""

    # Get each mission's faction, type, and modifiers
    for mission in ta_missions:
        # Add mission type and enemy faction to the embed
        ta_faction = db.worldstate.find_one({"key": mission["faction"]})["value"]
        ta_type = db.worldstate.find_one({"key": mission["missionType"]})["value"]
        ta_description += f"**{ta_type}** - {ta_faction}\n"

        # Get modifiers for both regular and elite difficulties
        ta_difficulties = mission["difficulties"]

        # Handle risks and deviations for normal difficulties
        ta_normal = ta_difficulties[0]
        normal_dev = string_split(ta_normal["deviation"])
        ta_description += f"Deviations {normal_dev}\n"

        normal_risks = ta_normal["risks"]
        ta_risks = []

        for risk in normal_risks:
            ta_risks.append(f"  - {string_split(risk)}")

        ta_description += f"Risks:{'\t'.join(ta_risks)}\n"

        # Handle additional risks for elite difficulties
        ta_elite = ta_difficulties[1]

        elite_risks = ta_elite["risks"]
        eta_risks = []

        for risk in elite_risks:
            eta_risks.append(f"  - {string_split(risk)}")

        ta_description += f"Elite Risks:{'\t'.join(eta_risks)}\n"

        # Get Temporal Archimedea variables
        ta_variables = ta["Variables"]
        parsed_variables = []

        for variable in ta_variables:
            parsed_variables.append(f"  - {string_split(variable)}")

        ta_description += f"Variables:{'\t'.join(parsed_variables)}"

    # Create the Deep Archimedea embed
    ta_embed = stoat.SendableEmbed(
        title=f"Temporal Archimedea {ta_duration}",
        description=ta_description,
        color=stoat.Colour.from_rgb(0, 128, 255),
    )

    return ta_embed


class Warframe(commands.Gear, name="Warframe"):
    """Commands for getting Warframe information"""

    GEAR_EMOJI = "⚔️"

    def __init__(self, bot: ChaosBot) -> None:
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
                "UrielVauban",
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
                "Follie",
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
        self.loop = asyncio.get_event_loop()

    def gear_load(self):
        self.loop.run_forever(self.daily_warframe())

    def gear_unload(self):
        self.loop.stop(self.daily_warframe())

    async def archimedea_timer(self):
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_wf_channels = db.warframe_channels.distinct("channel")
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(
                embeds=[deep_archimedea_status(self.worldstate_url)]
            )
            await daily_wf_channel.send(
                embeds=[temporal_archimedea_status(self.worldstate_url)]
            )

    async def archon_timer(self):
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_wf_channels = db.warframe_channels.distinct("channel")
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[archon_hunt(self.worldstate_url)])

    async def baro_timer(self):
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_wf_channels = db.warframe_channels.distinct("channel")
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[baro_kiteer(self.worldstate_url)])

    async def duviri_timer(self):
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_wf_channels = db.warframe_channels.distinct("channel")
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[duviri_status(self.worldstate_url)])

    # Handle all weekly Warframe tasks
    async def daily_warframe(self):
        archimedea_task = asyncio.create_task(
            schedule(
                delay=delay_until("Sunday", 21),
                loop_time=time_from_string(1, "week"),
                function=self.archimedea_timer(),
            )
        )
        archon_task = asyncio.create_task(
            schedule(
                delay=delay_until("Sunday", 21),
                loop_time=time_from_string(1, "week"),
                function=self.archon_timer(),
            )
        )
        baro_task = asyncio.create_task(
            schedule(
                delay=delay_until("Friday", 10),
                loop_time=time_from_string(1, "week"),
                function=self.baro_timer(),
            )
        )
        duviri_task = asyncio.create_task(
            schedule(
                delay=delay_until("Sunday", 21),
                loop_time=time_from_string(1, "week"),
                function=self.duviri_timer(),
            )
        )
        await archimedea_task
        await archon_task
        await baro_task
        await duviri_task

    @commands.command()
    async def alerts(self, ctx: commands.Context):
        """Find information on current alerts, if there are any"""
        alert_embed = await alerts_search(self.bot, self.worldstate_url)
        await ctx.send(embeds=[alert_embed])

    @commands.command()
    async def archon(self, ctx: commands.Context):
        """Find the current Archon, missions, and remaining time for the current hunt"""
        archon_embed = await archon_hunt(self.bot, self.worldstate_url)
        await ctx.send(embeds=[archon_embed])

    @commands.command()
    async def baro(self, ctx: commands.Context):
        """Get information on Baro Ki'Teer"""
        baro_embed = await baro_kiteer(self.bot, self.worldstate_url)
        await ctx.send(embeds=[baro_embed])

    @commands.command()
    async def deep_archimedea(self, ctx: commands.Context):
        """Get information on Deep Archimedea"""
        deep_embed = await deep_archimedea_status(self.bot, self.worldstate_url)
        await ctx.send(embeds=[deep_embed])

    @commands.command()
    async def duviri(self, ctx: commands.Context):
        """Find information on the current Duviri cycle rewards"""
        duviri_embed = await duviri_status(self.bot, self.worldstate_url)
        await ctx.send(embeds=[duviri_embed])

    @commands.command()
    async def nightwave(self, ctx: commands.Context):
        """Find information on the current Nightwave season and challenges"""
        nightwave_embed = await nightwave_status(self.bot, self.worldstate_url)
        await ctx.send(embeds=[nightwave_embed])

    @commands.command()
    async def sortie(self, ctx: commands.Context):
        """Find information on the current sortie"""
        sortie_embed = await sortie_status(self.bot, self.worldstate_url)
        await ctx.send(embeds=[sortie_embed])

    @commands.command()
    async def temporal_archimedea(self, ctx: commands.Context):
        """Get information on Temporal Archimedea"""
        temporal_embed = await temporal_archimedea_status(self.bot, self.worldstate_url)
        await ctx.send(embeds=[temporal_embed])

    @commands.command()
    async def progenitors(self, ctx: commands.Context):
        """Returns progenitor elements and their corresponding warframes"""
        progenitor_description = ""

        # Add fields for each element and corresponding warframes
        for key in self.progenitor:
            progenitors = ", ".join(self.progenitor[key])
            progenitor_description += f"**{key}** - {progenitors}\n"

        # Create the initial embed
        progenitor_embed = stoat.SendableEmbed(
            title="Progenitor Elements",
            description=progenitor_description,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        await ctx.send(embeds=[progenitor_embed])

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def set_warframe_channel(self, ctx: commands.Context, channel: str):
        """Takes in a channel link/ID and sets it as the automated Warframe channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        wf_channel_id = int(channel.split("/")[-1])
        # Prepares the new server & channel combination for this server
        new_channel = {"server": ctx.server.id, "channel": wf_channel_id}
        # Updates the Warframe channel for the server or inserts it if one doesn't exist currently
        db.warframe_channels.replace_one(
            {"server": ctx.server.id}, new_channel, upsert=True
        )

        # Let users know where the updated channel is
        updated_channel = ctx.server.get_channel(ctx.channel.id)
        if updated_channel:
            await ctx.send(
                f"Warframe content for this server will go to {updated_channel.name}."
            )

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def remove_warframe_channel(self, ctx: commands.Context):
        """Removes the automated Warframe channel for this server, if it exists."""

        # Removes the Warframe channel for the server if it exists
        if db.warframe_channels.find_one({"server": ctx.server.id}):
            db.warframe_channels.delete_one({"server": ctx.server.id})
            await ctx.send("Warframe automated content for this server is stopped.")
        # Lets the user know if there is no existing Warframe channel
        else:
            await ctx.send("There is no Warframe automated content for this server.")


def setup(bot: ChaosBot):
    bot.add_gear(Warframe(bot))
