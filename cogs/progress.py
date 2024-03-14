import nextcord
from pymongo import MongoClient
from os import getenv
from nextcord import Interaction
from nextcord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from aiohttp import ClientSession

client = MongoClient(getenv('CONN_STRING')) 
db = client.NextcordBot 

# Generates xp for a given message
def give_xp(message: nextcord.Message):
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

# Create a cog for levelling
class Progress(commands.Cog, name="Progress"):
    """Commands about economy/levelling."""

    COG_EMOJI = "📈"

    def __init__(self, bot) -> None:
      self.bot = bot

    # Code inspired 
    async def card_maker(self, interaction: Interaction, uid: int, guild_id: int):
        # Get user information from ID
        target = db.levels.find_one({"uid": uid, "guild": guild_id})
        user = self.bot.get_user(uid) if self.bot.get_user(uid) else uid
        username = user.display_name if self.bot.get_user(uid) else uid
        avatar_url = user.avatar.url if self.bot.get_user(uid) else None
        level = target["level"]
        xp = target["xp"]
        threshold = (level + 1) * 25
        progress = (xp / threshold) * 870
        textcard = "/main/assets/textcard.png"
        levelcard = "/main/assets/levelcard.png"
        font = "/main/assets/RobotoSlab-Regular.ttf"
        result = "/main/assets/result.png"
        avatar_mask = "/main/assets/avatar_mask.png"
        bar_mask = "/main/assets/bar_mask.png"

        # Get the avatar of the target user from URL
        async with ClientSession() as c:
            async with c.get(avatar_url) as resp:
                avatar = await resp.read()
        avatar = Image.open(BytesIO(avatar)).resize((170, 170))
        
        # Overlay the text card and avatar on the level card
        background = Image.open(levelcard)
        overlay = Image.open(textcard)
        background.paste(overlay, (200,0), overlay)
        a_mask = Image.open(avatar_mask).convert("L").resize((170,170))
        background.paste(avatar, (15, 15), a_mask)

        # Print username, level, and xp on the level card
        nameFont = ImageFont.truetype(font, 40)
        subFont = ImageFont.truetype(font, 30)
        draw = ImageDraw.Draw(background)
        draw.text((220, 20), username, font=nameFont, fill="white", stroke_width=1, stroke_fill=(0, 0, 0))
        draw.text((220, 150), f"Level - {level}", font=subFont, fill="white", stroke_width=1, stroke_fill=(0, 0, 0))
        draw.text((570, 150), f"{xp}/{threshold} XP", font=subFont, fill="white", stroke_width=1, stroke_fill=(0, 0, 0))

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
        await interaction.send(file=nextcord.File(result))     

    @commands.Cog.listener("on_message")
    async def xp(self, message: nextcord.Message):
        if message.author.bot:
            return
        author = message.author
        guild = message.guild
        channel = message.channel
        interaction = message.interaction
        person = message.author
        target = {"uid": author.id, "guild": guild.id}

        # If xp collection doesn't exist for server, make one
        if "levels" not in db.list_collection_names():
            db.create_collection("levels")

        # If member is not registered, create an entry for them
        if not db.levels.find_one(target):
            db.levels.insert_one({"uid": author.id, "guild": guild.id, "level": 0, "xp": 0})
        
        # Increase user xp and level as necessary
        user = db.levels.find_one(target)
        xp = user["xp"] + give_xp(message)
        level = user["level"]
        if level_up(xp, level):
            level += 1
            xp = 0
            if interaction is None:
                await channel.send(f"**{author.display_name}** reached level {level} on {guild}!")
            else:
                await Progress.card_maker(self, interaction, person.id, message.guild.id)
        db.levels.replace_one(target, {"uid": author.id, "guild": guild.id, "level": level, "xp": xp})

    @nextcord.slash_command()
    async def level(self, interaction: Interaction, person: nextcord.Member | nextcord.User | None = None):
        """Check level of a person, defaults to checking your own level"""
        if person is None:
            person = interaction.user
        target = {"uid": person.id, "guild": interaction.guild.id}
        record = db.levels.find_one(target)

        # Return XP and level or nothing if user is not registered
        if not record:
            return await interaction.send(f"{person.display_name} has no levels or XP!")
        else:
            return await Progress.card_maker(self, interaction, person.id, interaction.guild.id)
        
    @nextcord.slash_command()
    async def leaderboard(self, interaction: Interaction):
        """Gets the top 10 highest ranked people on the server"""
        server = interaction.guild
        # Sort the database for the highest 10 scoring on the server
        cursor = db.levels.find({"guild": server.id})
        leaders = cursor.sort([("level", -1), ("xp", -1)]).limit(10)
        embed = nextcord.Embed(title=f"{server.name} Leaderboard", color=nextcord.Colour.from_rgb(0, 128, 255))
        for position, leader in enumerate(leaders):
            # Get relevant information for each of the top 10
            uid = leader["uid"]
            user = self.bot.get_user(uid) if self.bot.get_user(uid) else uid
            username = user.display_name if self.bot.get_user(uid) else uid
            xp = leader["xp"]
            level = leader["level"]
            threshold = (level + 1) * 25
            embed.add_field(name=f"{position+1}. {username} Level: {level}", value=f"{xp}/{threshold} XP", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.guild.icon.url)
        await interaction.send(embed=embed)

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Progress(bot))