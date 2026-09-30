#!/usr/bin/env python
from io import BytesIO

import PIL.Image
import PIL.ImageChops
import PIL.ImageFile
import PIL.ImageFilter
from stoat.ext import commands

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


# Create a gear for image manipulation
class Image(commands.Gear, name="Image"):
    """Commands to do image manipulation."""

    GEAR_EMOJI = "📷"

    def __init__(self, bot: ChaosBot) -> None:
        self.bot = bot

    @commands.command()
    async def contrast_image(self, ctx: commands.Context, url: str, value: float = 1.5):
        """Increase image contrast by choosing a high value, decrease by choosing a low value, given its URL"""
        img_data = await self.bot.client.get_bytes(url)
        img: PIL.ImageFile.ImageFile = PIL.Image.open(img_data)

        out: PIL.Image.Image = img.point(lambda i: i * value)
        data = BytesIO()
        out.save(data, format="PNG")
        await ctx.channel.send(attachments=[("image.png", data.getvalue())])

    @commands.command()
    async def convert_image(self, ctx: commands.Context, url: str):
        """Convert an image to greyscale, given its URL"""
        img_data = await self.bot.client.get_bytes(url)
        img: PIL.ImageFile.ImageFile = PIL.Image.open(img_data)

        out: PIL.Image.Image = img.convert("L")
        data = BytesIO()
        out.save(data, format="PNG")
        await ctx.channel.send(attachments=[("image.png", data.getvalue())])

    @commands.command()
    async def filter_image(self, ctx: commands.Context, url: str, filter: str = "Blur"):
        """Apply filters to an image, given its URL"""
        # If the given filter is invalid, return an error message
        if filter.capitalize() not in filters:
            return await ctx.channel.send(
                f"Please try again with a valid filter: {list(filters.keys())}"
            )
        img_data = await self.bot.client.get_bytes(url)
        img: PIL.ImageFile.ImageFile = PIL.Image.open(img_data)

        out: PIL.Image.Image = img.filter(filters[filter.capitalize()])
        data = BytesIO()
        out.save(data, format="PNG")
        await ctx.channel.send(attachments=[("image.png", data.getvalue())])

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
        img_data = await self.bot.client.get_bytes(url)
        img: PIL.ImageFile.ImageFile = PIL.Image.open(img_data)

        if style.capitalize() == "Vertical":
            out: PIL.Image.Image = img.transpose(PIL.Image.Transpose.FLIP_TOP_BOTTOM)
        else:
            out: PIL.Image.Image = img.transpose(PIL.Image.Transpose.FLIP_LEFT_RIGHT)
        data = BytesIO()
        out.save(data, format="PNG")
        await ctx.channel.send(attachments=[("image.png", data.getvalue())])

    @commands.command()
    async def invert_image(self, ctx: commands.Context, url: str):
        """Invert the colours of an colour image, given its URL"""
        img_data = await self.bot.client.get_bytes(url)
        img: PIL.ImageFile.ImageFile = PIL.Image.open(img_data).convert("RGB")

        out = PIL.ImageChops.invert(img)
        data = BytesIO()
        out.save(data, format="PNG")
        await ctx.channel.send(attachments=[("image.png", data.getvalue())])


# Add the gear to the bot
async def setup(bot: ChaosBot):
    await bot.add_gear(Image(bot))
