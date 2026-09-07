#! usr/bin/env python
from io import BytesIO

import aiofiles
import stoat
from PIL import Image, ImageDraw, ImageFile, ImageFont
from stoat.ext import commands

from utilities import ChaosBot, db


# Create a gear for levelling
class Progress(commands.Gear, name="Progress"):
    """Commands about economy/levelling."""

    GEAR_EMOJI = "📈"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot

    async def card_maker(
        self, channel: stoat.TextableChannel, user_id: str, server_id: str
    ):
        # Get user information from ID
        with db.cursor() as cur:
            cur.execute(
                """SELECT level, xp FROM members WHERE (user_id, server_id) = (%s, %s) LIMIT 1""",
                (user_id, server_id),
            )
            level, xp = cur.fetchone()
        if self.bot.get_user(user_id):
            user = self.bot.get_user(user_id)
            username = user.display_name
            avatar_url = user.avatar.url()
        else:
            return await channel.send(f"Could not get user {user_id}!")

        # Gather information for the level card
        threshold = (level + 1) * 25
        progress = (xp / threshold) * 870
        textcard = "../assets/textcard.png"
        levelcard = "../assets/levelcard.png"
        font = "../assets/RobotoSlab-Regular.ttf"
        result = "../assets/result.png"
        avatar_mask = "../assets/avatar_mask.png"
        bar_mask = "../assets/bar_mask.png"

        # Get the avatar of the target user from URL
        avatar_bytes: bytes = await self.bot.client.get_bytes(avatar_url)
        avatar: ImageFile.ImageFile = Image.open(
            BytesIO(initial_bytes=avatar_bytes)
        ).resize((170, 170))

        # Overlay the text card and avatar on the level card
        background: ImageFile.ImageFile = Image.open(levelcard)
        overlay: ImageFile.ImageFile = Image.open(textcard)
        background.paste(overlay, (200, 0), overlay)
        a_mask: ImageFile.ImageFile = (
            Image.open(avatar_mask).convert("L").resize((170, 170))
        )
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
        b_mask: ImageFile.ImageFile = Image.open(bar_mask).convert("L")
        background.paste(img, (15, 225), b_mask)

        # Create and save the file and send it
        async with aiofiles.open(result, mode="wb") as file:
            background.save(file, "PNG")
            await channel.send(
                attachments=[stoat.Asset(filename="../assets/result.png")]
            )

    # Generates xp for a given message
    def give_xp(self, message: stoat.Message):
        words = message.content.split()
        if len(words) < 5:
            return 5
        else:
            return len(words)

    # Determines whether the user levels up or not; max level due to PostgreSQL int4 capacity
    # Capacity is 2147483647 and level 13107 is 2147254275
    def level_up(self, xp: int, level: int):
        threshold = (level + 1) * 25
        return xp >= threshold

    @commands.Gear.listener()
    async def xp(self, on: stoat.MessageCreateEvent):
        if on.message.author.bot:
            return
        author = on.message.author
        server = on.message.server
        channel = on.message.channel

        with db.cursor() as cur:
            cur.execute(
                """SELECT level, xp FROM members WHERE (user_id, server_id) = (%s, %s) LIMIT 1""",
                (author.id, server.id),
            )
            user = cur.fetchone()
            # If member is not registered, create an entry for them
            if not user:
                cur.execute(
                    "INSERT INTO members (user_id, server_id, level, xp) VALUES (%s, %s, %s, %s)",
                    (author.id, server.id, 0, 0),
                )
                db.commit()
                return
            # Increase user xp and level as necessary
            else:
                # Prevent users gaining more xp if they are already at the maximum level
                # For now, cap at 1000 but can go up to 13107 if needed
                level = user[0]
                if level > 1000:
                    return
                xp = user[1] + self.give_xp(on.message)
                if self.level_up(xp, level):
                    level += 1
                    xp = 0
                    await self.card_maker(channel, author.id, server.id)
                cur.execute(
                    "UPDATE members SET (level, xp) = (%s, %s) WHERE (user_id, server_id) = (%s, %s)",
                    (level, xp, author.id, server.id),
                )
                db.commit()

    @commands.command()
    async def level(
        self,
        ctx: commands.Context,
        person: stoat.Member | stoat.User | None,
    ):
        """Check level of a person, defaults to checking your own level"""
        if not person:
            person = ctx.user
        with db.cursor() as cur:
            cur.execute(
                """SELECT server_level, xp FROM levels WHERE member_id IN 
                (SELECT member_id FROM members WHERE (server_id, user_id) = (%s, %s)) LIMIT 1""",
                (ctx.server.id, person.id),
            )
            record = cur.fetchone()

        # Return XP and level or nothing if user is not registered
        if not record:
            return await ctx.send(f"{person.display_name} has no levels or XP!")
        else:
            return await self.card_maker(self, ctx.channel, person.id, ctx.server.id)

    @commands.command()
    async def leaderboard(self, ctx: commands.Context):
        """Gets the top 10 highest ranked people on the server"""
        server = ctx.server
        # Sort the database for the highest 10 scoring on the server
        with db.cursor() as cur:
            cur.execute(
                """SELECT user_id, level, xp FROM members
                ORDER BY level DESC NULLS LAST, xp DESC NULLS LAST LIMIT 10"""
            )
            leaders = cur.fetchall()
        embed_description = ""
        for position, leader in enumerate(leaders):
            # Get relevant information for each of the top 10
            user_id = leader[0]
            level = leader[1]
            xp = leader[2]

            user = self.bot.get_user(user_id) if self.bot.get_user(user_id) else user_id
            username = user.display_name if self.bot.get_user(user_id) else user_id
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
async def setup(bot: ChaosBot):
    await bot.add_gear(Progress(bot))
