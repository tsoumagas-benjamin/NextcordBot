# Common utilities that may be shared across files
from pymongo import MongoClient
from os import getenv
from stoat.ext import commands
from aiohttp import ClientSession
from json import loads
import datetime
from stoat import SendableEmbed
import asyncio

# TODO: Switch from MongoDB

# Database config
client = MongoClient(getenv("CONN_STRING"))

# Name our access to our client database
db = client.StoatBot

# Get all the existing collections
collections = db.list_collection_names()
collection_names = [
    "audit_logs",
    "birthdays",
    "daily_channels",
    "languages",
    "levels",
    "rules",
    "sales",
    "sales_channels",
    "warframe_channels",
    "worldstate",
]

days = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

permitted_servers: list[str] = [
    "01KHMHCAEVX96FMMA3FHEXZEKF",
    "01KHZYXDM1F104EQQ7V3ATRRER",
]


# Create a client session to be used for all async HTTP requests
class Client:
    def __init__(self) -> None:
        self._session = ClientSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.close()

    async def get_bytes(self, url):
        async with self._session.get(url) as r:
            output = r.read()
            return output

    async def get_text(self, url):
        async with self._session.get(url) as r:
            text_data = await r.text()
            output = loads(text_data)
            return output

    async def get_json(self, url):
        async with self._session.get(url) as r:
            output = await r.json()
            return output

    async def get_content(self, url):
        async with self._session.get(url) as r:
            output = await r.content()
            return output

    async def post(self, url, *args, **kwargs):
        async with self._session.post(url, *args, **kwargs) as r:
            post_content = await r.content()
            output = loads(post_content)
            return output

    async def close(self) -> None:
        if not self._session.closed:
            await self._session.close()


def check_permitted_servers(ctx: commands.Context):
    return ctx.server.id in permitted_servers


# Function to get the time in seconds until a given date and hour
def delay_until(day: str, hour: int):
    if (
        day.capitalize() not in days.keys()
        or day.capitalize() == "Tomorrow"
        or hour < 0
        or hour > 24
    ):
        return "Invalid date provided"

    # Get the next day coming up, i.e. the next Monday
    today = datetime.date.today()
    if day.capitalize == "Tomorrow":
        target_day = today + datetime.timedelta(days=1)
    else:
        target_day = today + datetime.timedelta(
            days=(days[day.capitalize] - today.weekday()) % 7
        )

    # Add the hours onto the date to make the datetime
    full_datetime = datetime.datetime(
        year=target_day.year, month=target_day.month, day=target_day.day, hour=hour
    )

    # Get the time from the target datetime to now in seconds
    delta = full_datetime - datetime.datetime.now()
    delay = delta.total_seconds()
    return delay


# Function to schedule a task to run after a given delay and time to loop
async def schedule(delay: float, loop_time: float, function, *args, **kwargs):
    await asyncio.sleep(delay)
    while True:
        await asyncio.gather(function(*args, **kwargs), asyncio.sleep(loop_time))


# Function to send embeds to the designated channel
async def send_embed(
    bot: commands.Bot, audit_channel_id: str, target_embed: SendableEmbed
):
    audit_channel = bot.get_channel(audit_channel_id)
    if audit_channel is None:
        audit_channel = await bot.fetch_channel(audit_channel_id)
    await audit_channel.send(embed=target_embed)


# Function to convert a string to time in seconds
def time_from_string(time: int, unit: str):
    match unit:
        case "week":
            return time * 604800
        case "day":
            return time * 86400
