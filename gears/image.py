import stoat
from stoat.ext import commands
import PIL.Image
import PIL.ImageFilter
from utilities import ChaosBot

filters = {
    "Blur": PIL.ImageFilter.BLUR,
    "Contour": PIL.ImageFilter.CONTOUR,
    "Detail": PIL.ImageFilter.DETAIL,
    "Edge Enhance": PIL.ImageFilter.EDGE_ENHANCE,
    "Edge Enhance More": PIL.ImageFilter.EDGE_ENHANCE_MORE,
    "Emboss": PIL.ImageFilter.EMBOSS,
    "Find Edges": PIL.ImageFilter.FIND_EDGES,
    "Sharpen": PIL.ImageFilter.SHARPEN,
    "Smooth": PIL.ImageFilter.SMOOTH,
    "Smooth More": PIL.ImageFilter.SMOOTH_MORE,
}


# Function to verify if an image is greyscale
def is_grey_scale(img_path):
    img = PIL.Image.open(img_path).convert("RGB")
    w, h = img.size
    for i in range(w):
        for j in range(h):
            r, g, b = img.getpixel((i, j))
            if r != g != b:
                return False
    return True


# Create a gear for image manipulation
class Image(commands.Gear, name="Image"):
    """Commands to do image manipulation."""

    GEAR_EMOJI = "📷"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot

    @commands.command()
    async def contrast_image(self, ctx: commands.Context, url: str, value: float = 1.5):
        """Increase image contrast by choosing a high value, decrease by choosing a low value, given its URL"""
        img_data = await self.bot.client.get_content(url)
        with open("../image.jpg", "wb") as handler:
            handler.write(img_data)
        im = PIL.Image.open("../image.jpg")
        if im:
            out = im.point(lambda i: i * value)
            out.save("../output.jpg")
            await ctx.channel.send(attachments=[stoat.Asset(filename="../output.jpg")])
        else:
            await ctx.channel.send("Could not load the image, sorry!")

    @commands.command()
    async def convert_image(self, ctx: commands.Context, url: str):
        """Convert an image to greyscale, given its URL"""
        img_data = await self.bot.client.get_content(url)
        with open("../image.jpg", "wb") as handler:
            handler.write(img_data)
        im = PIL.Image.open("../image.jpg")
        if im:
            out = im.convert("L")
            out.save("../output.jpg")
            await ctx.channel.send(attachments=[stoat.Asset(filename="../output.jpg")])
        else:
            await ctx.channel.send("Could not load the image, sorry!")

    @commands.command()
    async def filter_image(self, ctx: commands.Context, url: str, filter: str = "Blur"):
        """Apply filters to an image, given its URL"""
        # If the given filter is invalid, return an error message
        if filter.capitalize() not in filters.keys():
            return await ctx.channel.send(
                f"Please try again with a valid filter: {list(filters.keys())}"
            )
        img_data = await self.bot.client.get_content(url)
        with open("../image.jpg", "wb") as handler:
            handler.write(img_data)
        im = PIL.Image.open("../image.jpg")
        if im:
            out = im.filter(filters[filter.capitalize()])
            out.save("../output.jpg")
            await ctx.channel.send(attachments=[stoat.Asset(filename="../output.jpg")])
        else:
            await ctx.channel.send("Could not load the image, sorry!")

    @commands.command()
    async def flip_image(
        self,
        ctx: commands.Context,
        url: str,
        style: str = "Horizontal",
    ):
        """Flip an image vertically or horizontally, given its URL"""
        if style.capitalize() not in {"Horizontal", "Vertical"}:
            return await ctx.channel.send(
                "Please try again with a style of either `horizontal` or `vertical`"
            )
        img_data = await self.bot.client.get_content(url)
        with open("../image.jpg", "wb") as handler:
            handler.write(img_data)
        im = PIL.Image.open("../image.jpg")
        if im:
            if style.capitalize() == "Vertical":
                out = im.transpose(PIL.Image.Transpose.FLIP_TOP_BOTTOM)
            else:
                out = im.transpose(PIL.Image.Transpose.FLIP_LEFT_RIGHT)
            out.save("../output.jpg")
            await ctx.channel.send(attachments=[stoat.Asset(filename="../output.jpg")])
        else:
            await ctx.channel.send("Could not load the image, sorry!")

    @commands.command()
    async def invert_image(self, ctx: commands.Context, url: str):
        """Invert the colours of an colour image, given its URL"""
        img_data = await self.bot.client.get_content(url)
        with open("../image.jpg", "wb") as handler:
            handler.write(img_data)
        im = PIL.Image.open("../image.jpg")
        if is_grey_scale("../image.jpg"):
            return await ctx.channel.send(
                "This image doesn't contain any colour to invert!"
            )
        if im:
            r, g, b = im.split()
            out = PIL.Image.merge("RGB", (b, g, r))
            out.save("../output.jpg")
            await ctx.channel.send(attachments=[stoat.Asset(filename="../output.jpg")])
        else:
            await ctx.channel.send("Could not load the image, sorry!")


# Add the gear to the bot
def setup(bot: ChaosBot):
    bot.add_gear(Image(bot))
