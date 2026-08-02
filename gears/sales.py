#!/usr/bin/env python
import asyncio
from datetime import date, datetime, timedelta
from json import dumps
from os import getenv

import pytz
import stoat
from dotenv import load_dotenv
from stoat.ext import commands

from utilities import (
    ChaosBot,
    check_permitted_servers,
    db,
    delay_until,
    schedule,
    target_games,
    time_from_string,
)


# Create a gear for checking sales on games
class Sales(commands.Gear, name="Sales"):
    """Commands for checking for game sales"""

    GEAR_EMOJI = "💲"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot
        # Fetch the list of sales channels to post sale information to
        self.sales_channels = self.fetch_sales_channels()
        self.loop = asyncio.get_event_loop()

    def gear_load(self):
        self.loop.run_forever(self.daily_sales())

    def gear_unload(self):
        self.loop.stop(self.daily_sales())

    def fetch_sales_channels(self) -> list[str]:
        with db.cursor() as cur:
            cur.execute("SELECT channel_id FROM channels WHERE category = 'sales'")
            daily_channels = cur.fetchall()
        return daily_channels

    async def get_sales(self):
        # Run a function similar to update_sales where all games are checked for sales and the database is updated
        for game_id in target_games.values():
            await self.compare_cut(game_id)

    def prune_sales(self):
        # Delete all sales that expire before today or discounts less than or equal to 0%
        with db.cursor() as cur:
            cur.execute("DELETE FROM sales WHERE expiry < now() OR cut <= 0")
            db.commit()

    # Handle all daily sales related tasks
    async def daily_sales(self):
        sale_task = asyncio.create_task(
            schedule(
                delay=delay_until("Tomorrow", 12),
                loop_time=time_from_string(1, "day"),
                function=self.get_sales(),
            )
        )
        prune_task = asyncio.create_task(
            schedule(
                delay=delay_until("Tomorrow", 0),
                loop_time=time_from_string(1, "day"),
                function=self.prune_sales(),
            )
        )
        await sale_task
        await prune_task

    # Function to return a formatted URL to use for the GET request
    def get_base_url(self, substring: str):
        load_dotenv("../.env")
        base_url = (
            "https://api.isthereanydeal.com" + substring + "?key=" + getenv("DEAL_KEY")
        )
        return base_url

    # Function to get a game's ID on IsThereAnyDeal given it's title
    async def get_game_id(self, title: str):
        # Put the game title in lower case, separate each word and then join with +'s
        format_title = "+".join(title.lower().split())

        # Format the URL to query for looking up the game
        base_url = self.get_base_url("/games/lookup/v1")
        query_url = base_url + f"&title={format_title}"

        # Query the API and return the ID field
        game = await self.bot.client.get_json(query_url)
        game_id: str = game["game"]["id"]

        return game_id

    # Function to format expiry as a date object
    def format_expiry(self, expiry: str):
        # Isolate the year, month, and day parts of the string
        date_info = expiry.split("-")

        # Remove the leading zeroes and convert all strings to ints
        date = [date.lstrip("0") for date in date_info]
        year, month, day = list(map(int, date))

        # Create and return our date object
        expiry_date = datetime(year, month, day, 0, 0, 0, tzinfo=pytz.utc)

        return expiry_date

    # Function to return sale contents for a game
    async def get_sale_content(self, game_id: str):
        # Format game ID as a payload and set up header and API URL
        payload = [game_id]
        headers = {"content-type": "application/json"}
        sale_url = self.get_base_url("/games/prices/v3")

        # Make a POST request to the API and load the response as a python iterable object
        sale = await self.bot.client.post(
            url=sale_url, data=dumps(payload), headers=headers
        )

        return sale

    # Function to check for the best cut on a game and when it expires
    async def best_cut(self, game_id: str):

        # Make a POST request to the API and load the response as a python iterable object
        try:
            sale = await self.get_sale_content(game_id=game_id)
        except Exception as e:
            print(f"JSON for {game_id} could not be decoded because {e}")
            return

        # Gather information on the current best cut according to IsThereAnyDeal
        best_deal = sale[0]["deals"][0]
        best_cut = best_deal["cut"]
        expiry = best_deal["expiry"]
        if expiry:
            expiry_date = expiry[:10]
            return [best_cut, expiry_date]
        else:
            return [best_cut, None]

    # Function to return the corresponding title for a given game ID
    def get_title(self, game_id: str):
        for title, gid in target_games.items():
            if gid == game_id:
                return title

    # Function to format content to be sent to sales channels(see best_price())
    def format_sale(self, game_id: str):
        # Get the title and sale information for the game
        game_title = self.get_title(game_id)
        sale_json = self.get_sale_content(game_id)

        # Gather information on the historic lows for the game's price
        historic_low = sale_json[0]["historyLow"]
        all_time = historic_low["all"]["amount"]
        last_year = historic_low["y1"]["amount"]
        three_month = historic_low["m3"]["amount"]

        # Gather information on the current best deal according to IsThereAnyDeal
        best_deal = sale_json[0]["deals"][0]
        best_shop = best_deal["shop"]["name"]
        best_price = best_deal["price"]["amount"]
        best_cut = best_deal["cut"]
        deal_url = best_deal["url"]

        # Format sale description with best shop, price, discount, and sale history
        sale_description = f"Current best deal at {best_shop} for ${best_price} USD (-{best_cut}%) | {deal_url}\n"
        sale_description += f"All Time Low:\t${all_time} USD\n"
        sale_description += f"Last Year Low:\t${last_year} USD\n"
        sale_description += f"3 Month Low:\t${three_month} USD\n"

        # Create the embed to send with relevant information that was gathered
        sale_embed = stoat.SendableEmbed(
            title=f"Sale Information for {game_title.title()}",
            description=sale_description,
            color="blue",
        )

        return sale_embed

    # Function to report on all the active sales in the database
    def get_current_sales(self):
        sale_description = "Use /best_price on a game here to see more details\n"

        with db.cursor() as cur:
            cur.execute("SELECT * FROM sales")
            sales = cur.fetchall()

        for sale in sales:
            # Retrieve the game's title, discount, and expiry and format them for the embed
            sale_title = self.get_title(sale[0])
            sale_expiry = sale[2].strftime("%m-%d-%Y")
            sale_description += (
                f"**{sale_title}**:\t{sale[1]}% off until {sale_expiry}\n"
            )

        current_sale_embed = stoat.SendableEmbed(
            title="Current Sales on IsThereAnyDeal",
            description=sale_description,
            colour="blue",
        )

        return current_sale_embed

    # Function to send formatted content to sales channels
    async def send_sale_info(self, sale_embed: stoat.SendableEmbed):
        # Send a meme to each of the daily channels
        for channel_id in self.sales_channels:
            sales_channel = self.bot.get_channel(channel_id)
            if sales_channel is None:
                sales_channel = await self.bot.fetch_channel(channel_id)
            await sales_channel.send(embeds=[sale_embed()])

    # Function to store information on a game's sale cut and expiry in the database
    def store_sale(self, game_id: str, cut: int, expiry_date: date):
        # Overwrite the existing sale info or create a new entry if there is nothing
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO sales (sale_id, cut, expiry) VALUES (%s, %s, %s) 
                ON CONFLICT (sale_id) DO UPDATE SET cut = EXCLUDED.cut, expiry = EXCLUDED.expiry""",
                (game_id, cut, expiry_date),
            )
            db.commit()

        # Write to the servers about the new best sale
        self.send_sale_info(self.format_sale(game_id))

    # Function to compare a game's current best price against the database or append it if it's better
    async def compare_cut(self, game_id: str):
        # Get the current best sale info on a game
        try:
            current_best = await self.best_cut(game_id)
        except Exception as e:
            print(f"Could not retrieve current sale date for {game_id} because {e}")
            return
        current_best_cut = current_best[0]
        current_best_expiry = current_best[1]

        # If the best retrieved sale has a discount of 0, do not write it to the database
        if current_best_cut <= 0:
            print(f"Invalid sale for {game_id}")
            return

        # If there is no expiry, put the expiry as tomorrow
        if current_best_expiry is None:
            # Get today's date and increment it by one day to get tomorrow's date
            today = datetime.now(tz=pytz.utc).date()
            tomorrow = today + timedelta(days=1)
            current_best_expiry = tomorrow.strftime("%Y-%m-%d")

        formatted_expiry = self.format_expiry(current_best_expiry)

        # Check database for the if there is already a sale stored for this game
        with db.cursor() as cur:
            cur.execute("SELECT cut FROM sales WHERE sale_id = %s", [game_id])
            game_sale = cur.fetchone()

        if game_sale:
            # Check the cut for the existing record
            previous_cut = game_sale[0]

            # Replace previous sale if new sale is better
            if current_best_cut > previous_cut:
                self.store_sale(game_id, current_best_cut, formatted_expiry)

        # If a sale is not already recorded, record the new one
        else:
            self.store_sale(game_id, current_best_cut, formatted_expiry)

    # Function to set sales channel for this server
    @commands.command()
    @commands.check(check_permitted_servers)
    @commands.has_permissions(manage_server=True)
    async def set_sales_channel(self, ctx: commands.Context, channel: str):
        """Takes in a channel link/ID and sets it as the automated sales channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        sales_channel_id = int(channel.split("/")[-1])

        # Updates the sales channel for the server or inserts it if one doesn't exist currently
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO channels (server_id, category, channel_id) VALUES (%s, %s, %s) ON CONFLICT (server_id, category) DO UPDATE SET channel_id = EXCLUDED.channel_id",
                (ctx.server_id, "sales", sales_channel_id),
            )
            db.commit()

        # Let users know where the updated channel is
        updated_channel = ctx.server.get_channel(sales_channel_id)
        if updated_channel is None:
            updated_channel = await self.bot.fetch_channel(sales_channel_id)
        await ctx.send(f"Sales for this server will go to {updated_channel.name}.")

    # Function to remove sales channel for this server
    @commands.command()
    @commands.check(check_permitted_servers)
    @commands.has_permissions(manage_server=True)
    async def remove_sales_channel(self, ctx: commands.Context):
        """Removes the automated sales channel for this server, if it exists."""

        # Removes the sales channel if it exists
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM channels WHERE (server_id, category) = (%s, %s) LIMIT 1",
                (ctx.server.id, "sales"),
            )
            db.commit()
            if cur.rowcount == 0:
                return await ctx.channel.send(
                    "There is no sales channel for this server."
                )
            else:
                return await ctx.channel.send(
                    "Sales content for this server is stopped."
                )

    # Function to get the best price for a given game according to IsThereAnyDeal
    @commands.command()
    @commands.check(check_permitted_servers)
    async def best_price(self, ctx: commands.Context, game: str):
        """Searches IsThereAnyDeal for the best discount on a game given a title."""
        # Get the game's ID given its title
        try:
            game_id = await self.get_game_id(game)
        except Exception as e:
            await ctx.send("Unable to retrieve information on this game, sorry!")
            print(f"Best_price error: {e}")

        # Retrieve the embed with formatted information about the sale
        sale_embed = self.format_sale(game_id)

        await ctx.send(embeds=[sale_embed])

    # Function to get all current sales as an embed
    @commands.command()
    @commands.check(check_permitted_servers)
    async def current_sales(self, ctx: commands.Context):
        """Displays all currently stored game sales"""
        current_sale_embed = self.get_current_sales()

        await ctx.send(embeds=[current_sale_embed])

    # Function to fetch a game's ID on IsThereAnyDeal
    @commands.command()
    @commands.check(check_permitted_servers)
    @commands.has_permissions(manage_server=True)
    async def fetch_game_id(self, ctx: commands.Context, game: str):
        """Fetches the corresponding ID for a given game title, if possible"""
        # Get the game's ID given its title
        try:
            game_id = await self.get_game_id(game)
        except Exception as e:
            await ctx.send("Unable to retrieve the ID for this game, sorry!")
            print(f"fetch_game_id error: {e}")

        await ctx.send(f"ID for {game} is {game_id}")


def setup(bot: ChaosBot):
    bot.add_gear(Sales(bot))
