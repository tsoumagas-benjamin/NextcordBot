import nextcord, pymongo, os, re, wavelink, datetime
from nextcord import Interaction
from nextcord.ext import commands, application_checks

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

#Get all the existing collections
collections = db.list_collection_names()

#Get access to the songs collection
song_list = db['songs']

def title_case(s):
  return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(),s)

class Wave(commands.Cog, name="Wave"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to our lavalink nodes"""
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(
            bot=self.bot,
            host="lavalink.oops.wtf",
            port=443,
            password="www.freelavalink.ga",
            https=True
        )
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting"""
        print(f"Node: {node.identifier} is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track):
        interaction = player.interaction
        vc: player = interaction.guild.voice_client
        

        if vc.loop:
            return await vc.play(track)
        
        next_song = vc.queue.get()
        await vc.play(next_song)
        await interaction.send(f"Now playing: {next_song.title}")
    
    # @commands.command()
    # async def play(self, ctx: commands.Context, *, search: wavelink.YouTubeTrack):
    #     """Play a song with the given search query.
    #     If not connected, connect to our voice channel.
    #     """
    #     if not ctx.voice_client:
    #         vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    #     elif not getattr(ctx.author.voice, "channel", None):
    #         return await ctx.send("Join a voice channel first")
    #     else:
    #         vc: wavelink.Player = ctx.voice_client

        # if vc.queue.is_empty and vc.is_playing():
        #     await vc.play(search)
        #     await ctx.send(f"Now playing: {search.title}")
        # else:
        #     await vc.queue.put_wait(search)
        #     await ctx.send(f"Added {search.title} to the queue.")
        
        # vc.ctx = ctx
        # setattr(vc, "loop", False)

    @nextcord.slash_command(guild_ids=[686394755009347655])
    async def play(self, interaction: Interaction, search: str):
        """Plays a song in a voice channel."""
        search = await wavelink.YouTubeTrack.search(query=search, return_first=True)
        if not interaction.guild.voice_client:
            vc: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        else:
            vc: wavelink.Player = interaction.guild.voice_client
        
        if vc.queue.is_empty and not vc.is_playing():
            await vc.play(search)
            await interaction.send(f"Now playing: {search.title}")
        else:
            await vc.queue.put_wait(search)
            await interaction.send(f"Added {search.title} to the queue.")
        
        vc.interaction = interaction
        if vc.loop: 
            return
        setattr(vc, "loop", False)


    @commands.command()
    async def pause(self, ctx: commands.Context):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if not ctx.voice_client:
            return await ctx.send("Nothing is playing.")
        elif not getattr(ctx.author.voice, "channel", None):
            return await ctx.send("Join a voice channel first")
        else:
            vc: wavelink.Player = ctx.voice_client

        await vc.pause()
        await ctx.send("Music paused.")
    
    @commands.command()
    async def resume(self, ctx: commands.Context):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if not ctx.voice_client:
            return await ctx.send("Nothing is playing.")
        elif not getattr(ctx.author.voice, "channel", None):
            return await ctx.send("Join a voice channel first")
        else:
            vc: wavelink.Player = ctx.voice_client

        await vc.pause()
        await ctx.send("Music resumed.")

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if not ctx.voice_client:
            return await ctx.send("Nothing is playing.")
        elif not getattr(ctx.author.voice, "channel", None):
            return await ctx.send("Join a voice channel first.")
        else:
            vc: wavelink.Player = ctx.voice_client

        await vc.stop()
        await ctx.send("Music stopped.")
    
    @commands.command()
    async def disconnect(self, ctx: commands.Context):
        """Disconnects bot from voice channel."""
        if not ctx.voice_client:
            return await ctx.send("I am not in a voice channel.")
        elif not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        elif not ctx.author.voice == ctx.me.voice:
            return await ctx.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = ctx.voice_client
        await vc.disconnect()
        await ctx.send("Leaving the voice channel.")
    
    @commands.command()
    async def loop(self, ctx: commands.Context):
        """Loops current song."""
        if not ctx.voice_client:
            return await ctx.send("I am not in a voice channel.")
        elif not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        elif not ctx.author.voice == ctx.me.voice:
            return await ctx.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = ctx.voice_client
        
        try:
            vc.loop ^= True
        except Exception:
            setattr(vc, "loop", False)
        
        if vc.loop:
            return await ctx.send("Now looping the current song.")
        else:
            return await ctx.send("No longer looping the current song.")

    @commands.command()
    async def queue(self, ctx: commands.Context):
        """Returns songs in the queue."""
        if not ctx.voice_client:
            return await ctx.send("I am not in a voice channel.")
        elif not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        elif not ctx.author.voice == ctx.me.voice:
            return await ctx.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = ctx.voice_client

        if vc.queue.is_empty:
            return await ctx.send("Queue is empty")
        
        embed = nextcord.Embed(title="Queue", color=nextcord.Colour.from_rgb(225, 0, 255))
        queue = vc.queue.copy()
        song_count = 0
        for song in queue:
            song_count += 1
            embed.add_field(name=f"{song_count}.", value=f"`{song.title}`")
        
        return await ctx.send(embed=embed)
    
    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
        """Changes the music volume."""
        if not ctx.voice_client:
            return await ctx.send("I am not in a voice channel.")
        elif not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        elif not ctx.author.voice == ctx.me.voice:
            return await ctx.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = ctx.voice_client

        if volume < 0 or volume > 100:
            return await ctx.send("Volume must be between 0 and 100.")
        await ctx.send(f"Set the volume to {volume}%.")
        return await vc.set_volume(volume)
    
    @commands.command()
    async def nowplaying(self, ctx: commands.Context):
        """Returns the currently playing song"""
        if not ctx.voice_client:
            return await ctx.send("I am not in a voice channel.")
        elif not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        elif not ctx.author.voice == ctx.me.voice:
            return await ctx.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = ctx.voice_client
        
        if not vc.is_playing():
            return await ctx.send("Nothing is playing.")
        
        embed = nextcord.Embed(title=f"Now playing {vc.track.title}", description=f"Artist {vc.track.author}", color=nextcord.Colour.from_rgb(225, 0, 255))
        embed.add_field(name="Duration", value = f"{str(datetime.timedelta(seconds=vc.track.length))}")
        embed.add_field(name="Extra info", value=f"Song URL: [Click Me]({str(vc.track.uri)})")
    
def setup(bot):
    bot.add_cog(Wave(bot))