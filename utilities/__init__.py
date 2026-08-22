#!/usr/bin/env python
# Common utilities that may be shared across files
import asyncio
from datetime import datetime, timedelta
from json import loads
from os import getenv
from re import sub

import psycopg
import pytz
from aiohttp import ClientSession
from dotenv import load_dotenv
from stoat import Permissions, SendableEmbed
from stoat.ext import commands

# Name our access to our client database
load_dotenv(".env")
db: psycopg.Connection = psycopg.connect(
    f"dbname={getenv('DB_NAME')} user={getenv('DB_USER')}"
)

# Get all the existing collections
collection_names = [
    "birthdays",
    "channels",
    "levels",
    "members",
    "servers",
    "users",
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

# Define bot permissions, see: enums / UserPermissions
permissions = Permissions(
    manage_channels=False,
    manage_server=False,
    manage_roles=True,
    manage_customization=True,
    kick_members=True,
    ban_members=True,
    timeout_members=True,
    assign_roles=True,
    change_nickname=False,
    manage_nicknames=False,
    change_avatar=False,
    remove_avatars=False,
    view_channel=False,
    read_message_history=True,
    send_messages=True,
    manage_messages=True,
    manage_webhooks=False,
    create_invites=False,
    send_embeds=True,
    upload_files=True,
    use_masquerade=False,
    react=True,
    mention_everyone=False,
    mention_roles=False,
    connect=False,
    speak=False,
    video=False,
    mute_members=False,
    deafen_members=False,
    move_members=False,
    listen=False,
)

permitted_servers: list[str] = [
    "01KHMHCAEVX96FMMA3FHEXZEKF",
    "01KHZYXDM1F104EQQ7V3ATRRER",
]

target_games: dict = {
    "Balatro": "018d937f-700e-7161-9c8d-5423af1b7c99",
    "Blasphemous": "018d937f-046c-70c2-89ad-3db21e19f40f",
    "Blasphemous 2": "018d937f-6ee2-70f6-940c-6212ac74369e",
    "Blasphemous 2 Mea Culpa": "01921ec1-46fb-71a7-9ccf-c164312fcf97",
    "Death Must Die": "018d937f-701d-7262-bfce-91908d4a68bf",
    "Deep Rock Galactic": "018d937e-fdb1-704e-8962-3e822f2f223e",
    "Elden Ring": "018d937f-590c-728b-ac35-38bcff85f086",
    "Elden Ring Shadow of the Erdtree": "018dcc3c-5be6-7113-97c8-380547ec6cc3",
    "Hades": "018d937f-33f0-7200-80fc-87f769196c84",
    "Hades II": "018d937f-6ee3-738a-b578-ddd7e9a0d24d",
    "Nine Sols": "018d937f-6ee3-738a-b578-ddd7eb7b327d",
    "Ori and the Blind Forest Definitive Edition": "018d937f-1919-732b-82d4-9af60320b548",
    "Ori and the Will of the Wisps": "018d937f-3cc5-7116-b8e1-06ca7dd2e7ca",
    "Risk of Rain 2": "018d937f-1ad0-731b-a5bd-1937cb346030",
    "Risk of Rain 2 Alloyed Collective": "0196b61b-9226-7203-b2fd-1b743b30374b",
    "Risk of Rain 2 Seekers of the Storm": "018d9591-5076-72c7-8f9f-5814e4d41004",
    "Risk of Rain 2 Survivors of the Void": "018d937f-5db9-7246-b784-e94f402d7cd9",
    "SANABI": "018d937f-62fb-7394-b7df-25ff35798fe6",
    "Slay the Spire": "018d937f-285e-7065-a58b-23400688cc12",
    "Slay the Spire 2": "018ec8ff-e01c-70b6-bf65-5b184f82f859",
    "Terraria": "018d937f-30fa-705e-8a3a-f39719bdde93",
}


# Create a client session to be used for all async HTTP requests
class Client:
    def __init__(self) -> None:
        self._session = ClientSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.close()

    async def get_bytes(self, url) -> bytes:
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
            output = await r.json()
            return output

    async def close(self) -> None:
        if not self._session.closed:
            await self._session.close()


# Create a subclass for the bot to allow for extra customizability
class ChaosBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        # Forward all arguments, and keyword-only arguments to commands.Bot
        super().__init__(
            command_prefix="/",
        )

        # Custom bot attributes are set below
        self.client: Client = None
        self.loop: asyncio.AbstractEventLoop | None = None

    # Extend the existing setup_hook behaviour
    async def setup_hook(self):
        await super().setup_hook()
        # If the ClientSession for GET/POST requests isn't initialized, do so here
        if self.client:
            await self.client.close()
        self.client = Client()


def check_permitted_servers(ctx: commands.Context):
    return ctx.server.id in permitted_servers


# Function to get the time in seconds until a given date and hour
def delay_until(day: str, hour: int):
    if (
        (day.capitalize() not in days and day.capitalize() != "Tomorrow")
        or hour < 0
        or hour > 24
    ):
        return "Invalid date provided"

    # Get the next day coming up, i.e. the next Monday
    today = datetime.now(tz=pytz.utc).date()
    if day.capitalize() == "Tomorrow":
        target_day = today + timedelta(days=1)
    else:
        target_day = today + timedelta(
            days=(days[day.capitalize()] - today.weekday()) % 7
        )

    # Add the hours onto the date to make the datetime
    full_datetime: datetime = datetime(
        year=target_day.year,
        month=target_day.month,
        day=target_day.day,
        hour=hour,
        tzinfo=pytz.utc,
    )

    # Get the time from the target datetime to now in seconds
    delta = full_datetime - datetime.now(tz=pytz.utc)
    delay: float = delta.total_seconds()
    # If target has already passed, look for the day next week
    if delay < 0:
        full_datetime += timedelta(days=7)
        delta = full_datetime - datetime.now(tz=pytz.utc)
        delay: float = delta.total_seconds()
    return delay


# Function to convert an epoch timestamp into a dynamic timestamp
def epoch_convert(epoch: str):
    epoch_num = epoch[:10]
    formatted_time = f"<t:{epoch_num}:f>"
    return formatted_time


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
    await audit_channel.send(embeds=[target_embed])


# Function to put spaces before capitals in strings
def string_split(string: str):
    return sub(r"(?<!^)(?=[A-Z])", " ", string)


# Function to convert a string to time in seconds
def time_from_string(time: int, unit: str):
    match unit:
        case "week":
            return time * 604800
        case "day":
            return time * 86400
