import stoat
from stoat.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from utilities import db, Client

# TODO: Switch from MongoDB


# Generates xp for a given message
def give_xp(message: stoat.Message):
    words = message.content.split()
    if len(words) < 5:
        return 5
    else:
        return len(words)


# Determines whether the user levels up or not
def level_up(xp: int, level: int):
    threshold = (level + 1) * 25
    if xp >= threshold:
        return True
    else:
        return False


# Create a gear for levelling
class Progress(commands.Gear, name="Progress"):
    """Commands about economy/levelling."""

    GEAR_EMOJI = "📈"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def card_maker(self, ctx: commands.Context, uid: int, server_id: int):
        # Get user information from ID
        target = db.levels.find_one({"uid": uid, "server": server_id})
        if self.bot.get_user(uid):
            user = self.bot.get_user(uid)
            username = user.display_name
            avatar_url = user.avatar.url()
        else:
            return await ctx.send(f"Could not get user {uid}!")

        # Gather information for the level card
        level = target["level"]
        xp = target["xp"]
        threshold = (level + 1) * 25
        progress = (xp / threshold) * 870
        textcard = "../assets/textcard.png"
        levelcard = "../assets/levelcard.png"
        font = "../assets/RobotoSlab-Regular.ttf"
        result = "../assets/result.png"
        avatar_mask = "../assets/avatar_mask.png"
        bar_mask = "../assets/bar_mask.png"

        # Get the avatar of the target user from URL
        avatar_bytes = await Client.get_bytes(avatar_url)
        avatar = Image.open(BytesIO(avatar_bytes)).resize((170, 170))

        # Overlay the text card and avatar on the level card
        background = Image.open(levelcard)
        overlay = Image.open(textcard)
        background.paste(overlay, (200, 0), overlay)
        a_mask = Image.open(avatar_mask).convert("L").resize((170, 170))
        background.paste(avatar, (15, 15), a_mask)

        # Print username, level, and xp on the level card
        nameFont = ImageFont.truetype(font, 40)
        subFont = ImageFont.truetype(font, 30)
        draw = ImageDraw.Draw(background)
        draw.text(
            (220, 20),
            username,
            font=nameFont,
            fill="white",
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )
        draw.text(
            (220, 150),
            f"Level - {level}",
            font=subFont,
            fill="white",
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )
        draw.text(
            (570, 150),
            f"{xp}/{threshold} XP",
            font=subFont,
            fill="white",
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )

        # Draw progress bar on the level card
        img = Image.new("RGBA", (870, 50), (0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")
        draw.rounded_rectangle((0, 0, 870, 50), 25, fill=(255, 255, 255, 50))
        draw.rounded_rectangle((0, 0, progress, 50), 25, fill=(0, 128, 255))
        b_mask = Image.open(bar_mask).convert("L")
        background.paste(img, (15, 225), b_mask)

        # Create and save the file and send it
        file = open(result, "wb")
        background.save(file, "PNG")
        await ctx.send(attachments=[stoat.Asset(filename="../assets/result.png")])
        file.close()

    @commands.Gear.listener("on_message")
    async def xp(self, message: stoat.Message):
        if message.author.bot:
            return
        author = message.author
        server = message.server
        channel = message.channel
        ctx = message.ctx
        person = message.author
        target = {"uid": author.id, "server": server.id}

        # If xp collection doesn't exist for server, make one
        if "levels" not in db.list_collection_names():
            db.create_collection("levels")

        # If member is not registered, create an entry for them
        if not db.levels.find_one(target):
            db.levels.insert_one(
                {"uid": author.id, "server": server.id, "level": 0, "xp": 0}
            )

        # Increase user xp and level as necessary
        user = db.levels.find_one(target)
        xp = user["xp"] + give_xp(message)
        level = user["level"]
        if level_up(xp, level):
            level += 1
            xp = 0
            if ctx is None:
                await channel.send(
                    f"**{author.display_name}** reached level {level} on {server}!"
                )
            else:
                await self.card_maker(self, ctx, person.id, message.server.id)
        db.levels.replace_one(
            target, {"uid": author.id, "server": server.id, "level": level, "xp": xp}
        )

    @stoat.slash_command()
    async def level(
        self,
        ctx: commands.Context,
        person: stoat.Member | stoat.User | None = None,
    ):
        """Check level of a person, defaults to checking your own level"""
        if person is None:
            person = ctx.user
        target = {"uid": person.id, "server": ctx.server.id}
        record = db.levels.find_one(target)

        # Return XP and level or nothing if user is not registered
        if not record:
            return await ctx.send(f"{person.display_name} has no levels or XP!")
        else:
            return await self.card_maker(self, ctx, person.id, ctx.server.id)

    @stoat.slash_command()
    async def leaderboard(self, ctx: commands.Context):
        """Gets the top 10 highest ranked people on the server"""
        server = ctx.server
        # Sort the database for the highest 10 scoring on the server
        cursor = db.levels.find({"server": server.id})
        leaders = cursor.sort([("level", -1), ("xp", -1)]).limit(10)
        embed_description = ""
        for position, leader in enumerate(leaders):
            # Get relevant information for each of the top 10
            uid = leader["uid"]
            user = self.bot.get_user(uid) if self.bot.get_user(uid) else uid
            username = user.display_name if self.bot.get_user(uid) else uid
            xp = leader["xp"]
            level = leader["level"]
            threshold = (level + 1) * 25
            embed_description += (
                f"{position + 1}. {username}\tLevel: {level}\t{xp}/{threshold} XP\n"
            )
        embed_description += f"Requested by {ctx.author.display_name}"
        embed = stoat.SendableEmbed(
            title=f"{server.name} Leaderboard",
            color=stoat.Colour.from_rgb(0, 128, 255),
            icon_url=ctx.server.icon.url(),
        )
        await ctx.send(embeds=[embed])


# Add the gear to the bot
def setup(bot: commands.Bot):
    bot.add_gear(Progress(bot))
