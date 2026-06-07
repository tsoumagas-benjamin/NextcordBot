import stoat
from os import getenv
from stoat.ext import commands
from json import dumps
from datetime import datetime, date, timedelta
from utilities import (
    Client,
    db,
    check_permitted_servers,
    delay_until,
    schedule,
    time_from_string,
)
import asyncio

# TODO: Switch from MongoDB
# TODO: Test sales functions in Tinkering


# Create a gear for checking sales on games
class Sales(commands.Gear, name="Sales"):
    """Commands for checking for game sales"""

    GEAR_EMOJI = "💲"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Fetch the list of sales channels to post sale information to
        self.sales_channels = db.sales_channels.distinct("channel")
        self.loop = asyncio.get_event_loop()

    def gear_load(self):
        self.loop.run_forever(self.daily_sales())

    def gear_unload(self):
        self.loop.stop(self.daily_sales())

    # Dictionary of Game titles and IDs to regularly check for sales
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
        "Terraria": "018d937f-30fa-705e-8a3a-f39719bdde93",
    }

    def get_sales(self):
        # Run a function similar to update_sales where all games are checked for sales and the database is updated
        for game_id in self.target_games.values():
            self.compare_cut(game_id)

    def prune_sales(self):
        # Delete all sales with expiries older than the present datetime
        db.sales.delete_many({"expiry": {"$lt": datetime.now()}})

        # Delete all sales with discounts lower or equal to 0% if they exist
        db.sales.delete_many({"cut": {"$lte": 0}})

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
        base_url = (
            "https://api.isthereanydeal.com" + substring + "?key=" + getenv("DEAL_KEY")
        )
        return base_url

    # Function to get a game's ID on IsThereAnyDeal given it's title
    def get_game_id(self, title: str):
        # Put the game title in lower case, separate each word and then join with +'s
        format_title = "+".join(title.lower().split())

        # Format the URL to query for looking up the game
        base_url = self.get_base_url("/games/lookup/v1")
        query_url = base_url + f"&title={format_title}"

        # Query the API and return the ID field
        game = await Client.get_content(query_url)
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
        expiry_date = datetime(year, month, day, 0, 0, 0)

        return expiry_date

    # Function to return sale contents for a game
    def get_sale_content(self, game_id: str):
        # Format game ID as a payload and set up header and API URL
        payload = [game_id]
        headers = {"content-type": "application/json"}
        sale_url = self.get_base_url("/games/prices/v3")

        # Make a POST request to the API and load the response as a python iterable object
        sale = await Client.post(url=sale_url, data=dumps(payload), headers=headers)

        return sale

    # Function to check for the best cut on a game and when it expires
    def best_cut(self, game_id: str):

        # Make a POST request to the API and load the response as a python iterable object
        try:
            sale = self.get_sale_content(game_id=game_id)
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
        for title, id in self.target_games.items():
            if id == game_id:
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

        for sale in db.sales.find():
            # Retrieve the game's title, discount, and expiry and format them for the embed
            sale_title = self.get_title(sale["_id"])
            sale_expiry = sale["expiry"].strftime("%m-%d-%Y")
            sale_description += (
                f"**{sale_title}**:\t{sale['cut']}% off until {sale_expiry}\n"
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
        # Format the record to insert/replace the old record
        new_sale = {"_id": game_id, "cut": cut, "expiry": expiry_date}

        # Overwrite the existing sale info or create a new entry if there is nothing
        db.sales.replace_one({"_id": game_id}, new_sale, True)

        # Write to the servers about the new best sale
        self.send_sale_info(self.format_sale(game_id))

    # Function to compare a game's current best price against the database or append it if it's better
    def compare_cut(self, game_id: str):
        # Get the current best sale info on a game
        try:
            current_best = self.best_cut(game_id)
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
            today = date.today()
            tomorrow = today + timedelta(days=1)
            current_best_expiry = tomorrow.strftime("%Y-%m-%d")

        formatted_expiry = self.format_expiry(current_best_expiry)

        # Check database for the if there is already a sale stored for this game
        game_sale = db.sales.find_one(
            {"_id": game_id}, {"_id": False, "best_cut": True}
        )
        if game_sale:
            # Check the cut for the existing record
            previous_cut = game_sale["best_cut"]

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
    async def set_sales_channel(self, ctx: stoat.ctx, channel: str):
        """Takes in a channel link/ID and sets it as the automated sales channel for this server."""

        # Get the channel ID as an integer whether the user inputs a channel link or channel ID
        sales_channel_id = int(channel.split("/")[-1])
        # Prepares the new server & channel combination for this server
        new_channel = {"server": ctx.server_id, "channel": sales_channel_id}
        # Updates the sales channel for the server or inserts it if one doesn't exist currently
        db.sales_channels.replace_one(
            {"server": ctx.server_id}, new_channel, upsert=True
        )

        # Let users know where the updated channel is
        updated_channel = ctx.server.get_channel(sales_channel_id)
        if updated_channel is None:
            updated_channel = await self.bot.fetch_channel(sales_channel_id)
        await ctx.send(f"Sales for this server will go to {updated_channel.name}.")

    # Function to remove sales channel for this server
    @commands.command()
    @commands.check(check_permitted_servers)
    @commands.has_permissions(manage_server=True)
    async def remove_sales_channel(self, ctx: stoat.ctx):
        """Removes the automated sales channel for this server, if it exists."""

        # Removes the daily channel for the server if it exists
        if db.sales_channels.find_one({"server": ctx.server_id}):
            db.sales_channels.delete_one({"server": ctx.server_id})
            await ctx.send("Sales for this server are stopped.")

        # Lets the user know if there is no existing sales channel
        else:
            await ctx.send("There is no sales channel for this server.")

    # Function to get the best price for a given game according to IsThereAnyDeal
    @commands.command()
    @commands.check(check_permitted_servers)
    async def best_price(self, ctx: stoat.ctx, game: str):
        """Searches IsThereAnyDeal for the best discount on a game given a title."""
        # Get the game's ID given its title
        try:
            game_id = self.get_game_id(game)
        except Exception as e:
            await ctx.send("Unable to retrieve information on this game, sorry!")
            print(f"Best_price error: {e}")

        # Retrieve the embed with formatted information about the sale
        sale_embed = self.format_sale(game_id)

        await ctx.send(embeds=[sale_embed])

    # Function to get all current sales as an embed
    @commands.command()
    @commands.check(check_permitted_servers)
    async def current_sales(self, ctx: stoat.ctx):
        """Displays all currently stored game sales"""
        current_sale_embed = self.get_current_sales()

        await ctx.send(embeds=[current_sale_embed])

    # Function to fetch a game's ID on IsThereAnyDeal
    @commands.command()
    @commands.check(check_permitted_servers)
    @commands.has_permissions(manage_server=True)
    async def fetch_game_id(self, ctx: stoat.ctx, game: str):
        """Fetches the corresponding ID for a given game title, if possible"""
        # Get the game's ID given its title
        try:
            game_id = self.get_game_id(game)
        except Exception as e:
            await ctx.send("Unable to retrieve the ID for this game, sorry!")
            print(f"fetch_game_id error: {e}")

        await ctx.send(f"ID for {game} is {game_id}")


def setup(bot: commands.Bot):
    bot.add_gear(Sales(bot))
