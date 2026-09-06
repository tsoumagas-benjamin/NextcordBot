#!/usr/bin/env python
from datetime import datetime, timedelta

import pytz
import stoat
from apscheduler.triggers.cron import CronTrigger
from stoat.ext import commands

from utilities import (
    ChaosBot,
    db,
    epoch_convert,
    string_split,
)

# Credit to the WFCD for the Warframe worldstate parser API found here: https://api.warframestat.us/pc


class Warframe(commands.Gear, name="Warframe"):
    """Commands for getting Warframe information"""

    GEAR_EMOJI = "⚔️"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot
        # Create a dictionary of Warframe Progenitor types to retrieve later
        self.progenitor: dict = {
            "Impact": [
                "Baruuk",
                "Dante",
                "Gauss",
                "Grendel",
                "Rhino",
                "Sevagoth",
                "Sirius & Orion",
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
                "Uriel",
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
        self.worldstate_url = "https://api.warframestat.us/pc"
        # Store data and record when the last fetch to the API was
        self.last_fetch: datetime = datetime.now(tz=pytz.utc) - timedelta(minutes=5)
        self.worldstate_data = ""
        # Fetch the list of enrolled warframe channels to post daily content to
        self.daily_wf_channels = self.fetch_warframe_channels()

    async def gear_load(self):
        self.bot.scheduler.add_job(
            self.archimedea_timer,
            trigger=CronTrigger(day_of_week=6, hour=21, timezone=pytz.UTC),
        )
        self.bot.scheduler.add_job(
            self.archon_timer,
            trigger=CronTrigger(day_of_week=6, hour=21, timezone=pytz.UTC),
        )
        self.bot.scheduler.add_job(
            self.baro_timer,
            trigger=CronTrigger(day_of_week=4, hour=10, timezone=pytz.UTC),
        )
        self.bot.scheduler.add_job(
            self.duviri_timer,
            trigger=CronTrigger(day_of_week=6, hour=21, timezone=pytz.UTC),
        )

    def fetch_warframe_channels(self) -> list[str]:
        with db.cursor() as cur:
            cur.execute("SELECT channel_id FROM channels WHERE category = 'warframe'")
            daily_channels = cur.fetchall()
        return daily_channels

    # Function to perform a GET request on Warframe's worldstate URL
    async def request_wf_info(self):
        # If we have fetched less than 5 minutes ago use existing data instead of fetching again
        current_time = datetime.now(tz=pytz.utc)
        delta = current_time - self.last_fetch
        if delta.total_seconds() < 300:
            return self.worldstate_data
        try:
            # Return the parsed JSON as a Python object and update the last fetch time
            wf_world = await self.bot.client.get_json(self.worldstate_url)
            self.last_fetch = datetime.now(tz=pytz.utc)
            self.worldstate_data = wf_world
            return wf_world
        except Exception as error:
            return error

    # Function to get information on current alerts
    async def alerts_search(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about alerts
        alert_data = wf_world["alerts"]

        # Store all the alert information to pass to the embed
        alert_info = ""

        for alert in alert_data:
            # Get the start and end times as dynamic timestamps
            alert_start = epoch_convert(alert["activation"])
            alert_end = epoch_convert(alert["expiry"])

            # Get information on the alert location, type, faction, and difficulty
            alert_mission = alert["mission"]
            alert_node = alert_mission["node"]
            alert_type = alert_mission["type"]
            alert_faction = alert_mission["faction"]

            alert_min_level = alert_mission["minEnemyLevel"]
            alert_max_level = alert_mission["maxEnemyLevel"]
            alert_tag = alert["tag"]

            # Get information on the alert rewards
            alert_reward = alert["reward"]
            alert_credits = alert_reward["credits"]
            alert_items = alert_reward["countedItems"]

            # Get the alert tag and when it will be around
            alert_title = f"**{alert_tag}** from {alert_start} to {alert_end}\n"

            # Get the enemy level, faction, alert type and location
            alert_desc = f"Level {alert_min_level}-{alert_max_level} {alert_faction} {alert_type} on {alert_node}\n"

            # Append information about the alert
            alert_info += f"**{alert_title}**\t- {alert_desc}"

            # Append the alert credit reward
            alert_rewards = f"- {alert_credits} credits\n"

            # Get the type and quantity of additional rewards
            for item in alert_items:
                item_type = item["type"]
                item_count = item["count"]
                alert_rewards += f"- {item_count} {item_type}\n"

            alert_info += f"**Rewards:**\n{alert_rewards}"

        # Create an embed object to return with alert information
        alert_embed = stoat.SendableEmbed(
            title="Alerts",
            description=alert_info,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return alert_embed

    # Function to get information on this week's archon hunt
    async def archon_hunt(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about Archon Hunts
        archon_info = wf_world["archonHunt"]

        # Convert the Archon's arrival and expiry as dynamic timestamps
        archon_start = epoch_convert(archon_info["activation"])
        archon_end = epoch_convert(archon_info["expiry"])
        archon_duration = f"{archon_start} - {archon_end}"

        # Get the current Archon and the missions leading up to them
        hunt_info = []
        current_archon = archon_info["boss"]
        archon_missions = archon_info["missions"]

        # Append each mission type and node
        for mission in archon_missions:
            hunt_info.append(f"{mission['type']} - {mission['node']}")

        # Create an embed object to return with Archon information
        archon_embed = stoat.SendableEmbed(
            title=f"{current_archon} is here between {archon_duration}",
            description="\n".join(hunt_info),
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return archon_embed

    # Function to handle retrieving when Baro Ki'Teer will arrive or if he is here currently
    async def baro_kiteer(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about Baro Ki'Teer
        baro = wf_world["voidTrader"]

        # Get the start and end times as dynamic timestamps
        baro_start = epoch_convert(baro["activation"])
        baro_end = epoch_convert(baro["expiry"])
        baro_duration = f"{baro_start} - {baro_end}"

        # Get Baro's location and inventory
        baro_location = baro["location"] if baro["location"] else "Location Unknown"
        baro_inventory = baro["inventory"]
        if not baro_inventory:
            # Create an embed object to return with Baro information
            baro_embed = stoat.SendableEmbed(
                title=f"Baro Ki'Teer will be at {baro_location} between {baro_duration}",
                description="Inventory Unknown",
                color=stoat.Colour.from_rgb(0, 128, 255),
            )
            return baro_embed
        else:
            baro_list = []

            # Iterate Baro's inventory
            for item in baro_inventory:
                # Get each item's name, ducat, and credit cost
                ducats = item["ducats"]
                wf_credits = item["credits"]
                name = item["item"]

                # Format everything into one line and append it to the list
                baro_list.append(f"{name} - {ducats} D {wf_credits} C")

        # Create an embed object to return with Baro information
        baro_embed = stoat.SendableEmbed(
            title=f"Baro Ki'Teer is at {baro_location} between {baro_duration}",
            description=baro_list,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return baro_embed

    # Function to get information on this week's calendar status/rewards
    async def calendar_status(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about the calendar in 1999
        calendar = wf_world["calendar"]

        # Get the start and end time for this Duviri week as dynamic timestamps
        calendar_start = epoch_convert(calendar["activation"])
        calendar_end = epoch_convert(calendar["expiry"])
        calendar_duration = f"{calendar_start} - {calendar_end}"

        # Iterate days and only record days with rewards
        calendar_rewards = "Calendar Rewards\n"
        for day in calendar["days"]:
            if len(day["events"]) == 2:
                rewards = day["events"]
                calendar_rewards += f"{day['date'][:10]}\t{rewards[0]['reward']} or {rewards[1]['reward']}"

        # Create an embed object to return with calendar information
        calendar_embed = stoat.SendableEmbed(
            title=f"{calendar['season']} - {calendar_duration}",
            description=f"{calendar_rewards}",
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return calendar_embed

    # Function to get information on the current Deep Archimedea
    async def deep_archimedea_status(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about sorties
        da = wf_world["archimedeas"][0]

        # Get the start and end times as dynamic timestamps
        da_start = epoch_convert(da["activation"])
        da_end = epoch_convert(da["expiry"])
        da_duration = f"{da_start} - {da_end}"

        # Get the Deep Archimedea missions
        da_missions = da["missions"]

        # Store information on the deep archimedea
        da_description = ""

        # Get each mission's faction, type, and modifiers
        for mission in da_missions:
            # Add mission type and enemy faction to the embed
            da_faction = mission["faction"]
            da_type = mission["missionType"]
            da_description += f"**{da_type}** - {da_faction}\n"

            # Handle risks and deviations
            da_dev = mission["deviation"]["name"]
            da_risk = mission["risks"][0]["name"]
            eda_risk = mission["risks"][1]["name"]

            da_description += f"Deviations {da_dev}\n"
            da_description += f"Risk: {da_risk}\n"
            da_description += f"Elite Risk: {eda_risk}\n"

        # Get Deep Archimedea variables
        da_variables = da["personalModifiers"]
        parsed_variables = []

        for variable in da_variables:
            parsed_variables.append(f"  - {string_split(variable['name'])}")

        da_description += f"Variables:{'\t'.join(parsed_variables)}"

        # Create the Deep Archimedea embed
        da_embed = stoat.SendableEmbed(
            title=f"Deep Archimedea {da_duration}",
            description=da_description,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return da_embed

    # Function to handle the retrieval of Duviri information
    async def duviri_status(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about Duviri
        duviri = wf_world["duviriCycle"]

        # Look in both regular and steel path variants for reward choices
        regular_choices = duviri["choices"][0]
        steel_path_choices = duviri["choices"][1]

        rewards = []
        sp_rewards = []

        for choice in regular_choices:
            rewards.append(f"- {choice}")

        for choice in steel_path_choices:
            sp_rewards.append(f"- {string_split(choice)} Incarnon Genesis")

        duviri_regular = "\n".join(rewards)
        duviri_steel_path = "\n".join(sp_rewards)

        duviri_description = f"**Circuit Rewards** (Choose one)\n{duviri_regular}\n"
        duviri_description += (
            f"**Steel Path Circuit Rewards** (Choose two)\n{duviri_steel_path}\n"
        )

        # Create an embed object to return with Duviri information
        duviri_embed = stoat.SendableEmbed(
            title="Weekly Duviri Rewards",
            description=duviri_description,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return duviri_embed

    # Function to get information on Nightwave
    async def nightwave_status(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about Nightwave
        nw = wf_world["nightwave"]

        # Get the start and end time for the Nightwave Season as dynamic timestamps
        nw_start = epoch_convert(nw["activation"])
        nw_end = epoch_convert(nw["expiry"])
        nw_duration = f"{nw_start} - {nw_end}"

        # Get the current Nightwave season
        nw_season = nw["season"]

        # Get the current Nightwave challenges
        nw_challenges = nw["activeChallenges"]

        # Create a string with the current Nightwave season
        nw_title = f"**Nightwave Season {nw_season}**"

        challenge_info = ""

        for challenge in nw_challenges:
            # Get whether the challenge is daily or weekly
            try:
                if challenge["isDaily"]:
                    duration = "Daily"
            except Exception:
                duration = "Weekly"

            # Get the start and end time for the challenge
            start = epoch_convert(challenge["activation"])
            end = epoch_convert(challenge["expiry"])

            # Get the requirement and reward for the challenge
            requirement_name = challenge["title"]
            requirement_desc = challenge["desc"]
            requirement = f"{requirement_name} - {requirement_desc}"
            reward = challenge["reputation"]

            challenge_info += f"- ({duration}) {reward} {requirement} {start}-{end}\n"

        # Create an embed object to return with Nightwave information
        nw_embed = stoat.SendableEmbed(
            title=f"{nw_title} - {nw_duration}",
            description=f"Rewards:\n{challenge_info}",
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return nw_embed

    # Function to get information on the current sortie
    async def sortie_status(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about sorties
        sortie = wf_world["sortie"]

        # Get the start and end time for sorties as a dynamic timestamp
        sortie_start = epoch_convert(sortie["activation"])
        sortie_end = epoch_convert(sortie["expiry"])

        # Get the sortie boss and missions
        sortie_boss = sortie["boss"]
        missions = sortie["variants"]

        # Create the message for when the sortie will be around
        sortie_title = f"**Sortie** {sortie_boss} from {sortie_start} to {sortie_end}\n"
        sortie_missions = ""

        # Get each missions type, modifier, and node
        for mission in missions:
            sortie_type = mission["missionType"]
            sortie_modifier = mission["modifier"]
            sortie_node = mission["node"]
            sortie_missions += f"{sortie_type} {sortie_node} {sortie_modifier}\n"

        # Create an embed object to return with sortie information
        sortie_embed = stoat.SendableEmbed(
            title=sortie_title,
            description=sortie_missions,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return sortie_embed

    # Function to get information on the current Temporal Archimedea
    async def temporal_archimedea_status(self):
        # Convert the response content for the world state into a Python object
        wf_world = await self.request_wf_info()

        # Access specifically the information about sorties
        ta = wf_world["archimedeas"][1]

        # Get the start and end times as dynamic timestamps
        ta_start = epoch_convert(ta["activation"])
        ta_end = epoch_convert(ta["expiry"])
        ta_duration = f"{ta_start} - {ta_end}"

        # Get the Temporal Archimedea missions
        ta_missions = ta["missions"]

        # Store information on the Temporal Archimedea
        ta_description = ""

        # Get each mission's faction, type, and modifiers
        for mission in ta_missions:
            # Add mission type and enemy faction to the embed
            ta_faction = mission["faction"]
            ta_type = mission["missionType"]
            ta_description += f"**{ta_type}** - {ta_faction}\n"

            # Handle risks and deviations
            ta_dev = mission["deviation"]["name"]
            ta_risk = mission["risks"][0]["name"]
            eta_risk = mission["risks"][1]["name"]

            ta_description += f"Deviations {ta_dev}\n"
            ta_description += f"Risk: {ta_risk}\n"
            ta_description += f"Elite Risk: {eta_risk}\n"

        # Get Temporal Archimedea variables
        ta_variables = ta["personalModifiers"]
        parsed_variables = []

        for variable in ta_variables:
            parsed_variables.append(f"  - {string_split(variable['name'])}")

        ta_description += f"Variables:{'\t'.join(parsed_variables)}"

        # Create the Deep Archimedea embed
        ta_embed = stoat.SendableEmbed(
            title=f"Temporal Archimedea {ta_duration}",
            description=ta_description,
            color=stoat.Colour.from_rgb(0, 128, 255),
        )

        return ta_embed

    async def archimedea_timer(self):
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[self.deep_archimedea_status()])
            await daily_wf_channel.send(embeds=[self.temporal_archimedea_status()])

    async def archon_timer(self):
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[self.archon_hunt()])

    async def baro_timer(self):
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[self.baro_kiteer()])

    async def duviri_timer(self):
        # Send the content to each of the daily warframe channels
        for channel_id in self.daily_wf_channels:
            daily_wf_channel = self.bot.get_channel(channel_id)
            if daily_wf_channel is None:
                daily_wf_channel = await self.bot.fetch_channel(channel_id)
            await daily_wf_channel.send(embeds=[self.duviri_status()])

    @commands.command()
    async def alerts(self, ctx: commands.Context):
        """Find information on current alerts, if there are any"""
        alert_embed = await self.alerts_search()
        await ctx.send(embeds=[alert_embed])

    @commands.command()
    async def archon(self, ctx: commands.Context):
        """Find the current Archon, missions, and remaining time for the current hunt"""
        archon_embed = await self.archon_hunt()
        await ctx.send(embeds=[archon_embed])

    @commands.command()
    async def baro(self, ctx: commands.Context):
        """Get information on Baro Ki'Teer"""
        baro_embed = await self.baro_kiteer()
        await ctx.send(embeds=[baro_embed])

    @commands.command()
    async def deep_archimedea(self, ctx: commands.Context):
        """Get information on Deep Archimedea"""
        deep_embed = await self.deep_archimedea_status()
        await ctx.send(embeds=[deep_embed])

    @commands.command()
    async def duviri(self, ctx: commands.Context):
        """Find information on the current Duviri cycle rewards"""
        duviri_embed = await self.duviri_status()
        await ctx.send(embeds=[duviri_embed])

    @commands.command()
    async def nightwave(self, ctx: commands.Context):
        """Find information on the current Nightwave season and challenges"""
        nightwave_embed = await self.nightwave_status()
        await ctx.send(embeds=[nightwave_embed])

    @commands.command()
    async def sortie(self, ctx: commands.Context):
        """Find information on the current sortie"""
        sortie_embed = await self.sortie_status()
        await ctx.send(embeds=[sortie_embed])

    @commands.command()
    async def temporal_archimedea(self, ctx: commands.Context):
        """Get information on Temporal Archimedea"""
        temporal_embed = await self.temporal_archimedea_status()
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

        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO channels (server_id, category, channel_id) VALUES (%s, %s, %s) 
                ON CONFLICT (server_id, category) DO UPDATE SET channel_id = EXCLUDED.channel_id""",
                (ctx.server.id, "warframe", wf_channel_id),
            )
            db.commit()

        # Let users know where the updated channel is
        updated_channel = ctx.server.get_channel(ctx.channel.channel_id)
        if updated_channel:
            return await ctx.channel.send(
                f"Warframe content for this server will go to {updated_channel.name}."
            )

    @commands.command()
    @commands.has_permissions(manage_server=True)
    async def remove_warframe_channel(self, ctx: commands.Context):
        """Removes the automated Warframe channel for this server, if it exists."""

        # Removes the warframe channel if it exists
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM channels WHERE (server_id, category) = (%s, %s) LIMIT 1",
                (ctx.server.id, "warframe"),
            )
            db.commit()
            if cur.rowcount == 0:
                return await ctx.channel.send(
                    "There is no warframe channel for this server."
                )
            else:
                return await ctx.channel.send(
                    "Warframe content for this server is stopped."
                )


async def setup(bot: ChaosBot):
    await bot.add_gear(Warframe(bot))
