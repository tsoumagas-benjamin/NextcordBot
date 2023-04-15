import nextcord, aiohttp
from nextcord import Interaction
from nextcord.ext import commands, application_checks
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO

#Get image from URL, and return it.
async def get_image(interaction, url) -> nextcord.File | None:
   async with aiohttp.ClientSession() as ses:
      async with ses.get(url) as r:
            try:
                image = await r.read()
                with BytesIO(image) as file:
                    img_file = nextcord.File(file, "GeneratedImage.png")
                    await ses.close()
                    return img_file
            except:
                await ses.close()
                await interaction.send("Could not open image link!")
                return None
            
filters = {
    "Blur": ImageFilter.BLUR, 
    "Contour": ImageFilter.CONTOUR,
    "Detail": ImageFilter.DETAIL,
    "Edge Enhance": ImageFilter.EDGE_ENHANCE,
    "Edge Enhance More": ImageFilter.EDGE_ENHANCE_MORE,
    "Emboss": ImageFilter.EMBOSS,
    "Find Edges": ImageFilter.FIND_EDGES,
    "Sharpen": ImageFilter.SHARPEN,
    "Smooth": ImageFilter.SMOOTH,
    "Smooth More": ImageFilter.SMOOTH_MORE
}

#Create a cog for image manipulation
class Image(commands.Cog, name="Image"):
    """Commands to do image manipulation."""

    COG_EMOJI = "📷"

    def __init__(self, bot) -> None:
      self.bot = bot

    @nextcord.slash_command(name="flip")
    async def flip_image(self, interaction: Interaction, url: str, style: str = nextcord.SlashOption(name="orientation", description="Flip vertically or horizontally", choices=["Vertical", "Horizontal"])):
        """Flip an image vertically or horizontally, given its URL"""
        image = await get_image(interaction, url)
        im = Image.open(image)
        if im:
            if style == "Vertical":
                out = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            else:
                out = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            await interaction.send(file=out)
        else:
            await interaction.send("Could not load the image, sorry!")
    
    @nextcord.slash_command(name="convert")
    async def convert_image(self, interaction: Interaction, url: str, style: str = nextcord.SlashOption(name="conversion", description="Convert to greyscale or colour", choices=["Greyscale", "Colour"])):
        """Convert an image to greyscale or colour, given its URL"""
        image = await get_image(interaction, url)
        im = Image.open(image)
        if image:
            mode = "L" if style == "Greyscale" else "RGB"
            out = im.convert(mode)
            await interaction.send(file=out)
        else:
            await interaction.send("Could not load the image, sorry!")
    
    @nextcord.slash_command(name="filter")
    async def filter_image(self, interaction: Interaction, url: str, filter: str = nextcord.SlashOption(name="filters", description="Choose a filter to apply to the image", choices=filters.keys())):
        """Apply filters to an image, given its URL"""
        image = await get_image(interaction, url)
        im = Image.open(image)
        if im:
            out = im.filter(filters[filter])
            await interaction.send(file=out)
        else:
            await interaction.send("Could not load the image, sorry!")

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Image(bot))