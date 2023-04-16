import nextcord, requests, cv2
from nextcord import Interaction
from nextcord.ext import commands
import PIL.Image, PIL.ImageFilter
            
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
    "Smooth More": PIL.ImageFilter.SMOOTH_MORE
}

# Function to verify if an image is greyscale
def is_grey_scale(img_path):
    img = Image.open(img_path).convert('RGB')
    w, h = img.size
    for i in range(w):
        for j in range(h):
            r, g, b = img.getpixel((i,j))
            if r != g != b: 
                return False
    return True

#Create a cog for image manipulation
class Image(commands.Cog, name="Image"):
    """Commands to do image manipulation."""

    COG_EMOJI = "📷"

    def __init__(self, bot) -> None:
      self.bot = bot
    
    @nextcord.slash_command(name="convert")
    async def convert_image(self, interaction: Interaction, url: str, style: str = "Greyscale"):
        """Convert an image to greyscale, given its URL"""
        img_data = requests.get(url).content
        with open('../image.jpg', 'wb') as handler:
            handler.write(img_data)
        im = PIL.Image.open('../image.jpg')
        if im:
            out = im.convert("L")
            out.save("../output.jpg")
            await interaction.send(file=nextcord.File("../output.jpg"))
        else:
            await interaction.send("Could not load the image, sorry!")
    
    @nextcord.slash_command(name="filter")
    async def filter_image(self, interaction: Interaction, url: str, filter: str = nextcord.SlashOption(name="filters", description="Choose a filter to apply to the image", choices=filters.keys())):
        """Apply filters to an image, given its URL"""
        img_data = requests.get(url).content
        with open('../image.jpg', 'wb') as handler:
            handler.write(img_data)
        im = PIL.Image.open('../image.jpg')
        if im:
            out = im.filter(filters[filter])
            out.save("../output.jpg")
            await interaction.send(file=nextcord.File("../output.jpg"))
        else:
            await interaction.send("Could not load the image, sorry!")
    
    @nextcord.slash_command(name="flip")
    async def flip_image(self, interaction: Interaction, url: str, style: str = nextcord.SlashOption(name="orientation", description="Flip vertically or horizontally", choices=["Vertical", "Horizontal"])):
        """Flip an image vertically or horizontally, given its URL"""
        img_data = requests.get(url).content
        with open('../image.jpg', 'wb') as handler:
            handler.write(img_data)
        im = PIL.Image.open('../image.jpg')
        if im:
            if style == "Vertical":
                out = im.transpose(PIL.Image.Transpose.FLIP_TOP_BOTTOM)
            else:
                out = im.transpose(PIL.Image.Transpose.FLIP_LEFT_RIGHT)
            out.save("../output.jpg")
            await interaction.send(file=nextcord.File("../output.jpg"))
        else:
            await interaction.send("Could not load the image, sorry!")
    
    @nextcord.slash_command(name="invert")
    async def invert_image(self, interaction: Interaction, url: str):
        """Invert the colours of an colour image, given its URL"""
        img_data = requests.get(url).content
        with open('../image.jpg', 'wb') as handler:
            handler.write(img_data)
        im = PIL.Image.open('../image.jpg')
        if is_grey_scale('../image.jpg'):
            return await interaction.send("This image doesn't contain any colour to invert!")
        if im:
            r, g, b = im.split()
            out = PIL.Image.merge("RGB", (b, g, r))
            out.save("../output.jpg")
            await interaction.send(file=nextcord.File("../output.jpg"))
        await interaction.send("Could not load the image, sorry!")

#Add the cog to the bot
def setup(bot):
    bot.add_cog(Image(bot))