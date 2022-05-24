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

default_volume = 5

def title_case(s):
  return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(),s)

class Music(commands.Cog, name="Music"):
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
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.YouTubeTrack, reason):
        interaction = player.interaction
        vc: player = interaction.guild.voice_client

        if vc.loop:
            return await vc.play(track)
        
        next_song = vc.queue.get()
        await vc.play(next_song)
        await interaction.send(f"Now playing: {next_song.title}")

    @nextcord.slash_command()
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
            await vc.set_volume(default_volume)
            await vc.play(search)
            await interaction.send(f"Now playing: {search.title}")
        else:
            await vc.queue.put_wait(search)
            await interaction.send(f"Added {search.title} to the queue.")
        
        vc.interaction = interaction
        try:
            if vc.loop: return
        except Exception:
            setattr(vc, "loop", False)

    @nextcord.slash_command()
    async def pause(self, interaction: Interaction):
        """Pauses the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.pause()
        await interaction.send("Music paused.")
    
    @nextcord.slash_command()
    async def resume(self, interaction: Interaction):
        """Resumes the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.resume()
        await interaction.send("Music resumed.")

    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        """Stops the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.stop()
        await interaction.send("Music stopped.")

    @nextcord.slash_command()
    async def disconnect(self, interaction: Interaction):
        """Disconnects the bot from the voice channel."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.disconnect()
        await interaction.send("Left the voice channel.")

    @nextcord.slash_command()
    async def loop(self, interaction: Interaction):
        """Loops current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client
        
        try:
            vc.loop ^= True
        except Exception:
            setattr(vc, "loop", False)
        
        if vc.loop:
            return await interaction.send("Now looping the current song.")
        else:
            return await interaction.send("No longer looping the current song.")

    @nextcord.slash_command()
    async def queue(self, interaction: Interaction):
        """Returns songs in the queue."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        if vc.queue.is_empty:
            return await interaction.send("Queue is empty")
        
        embed = nextcord.Embed(title="Queue", color=nextcord.Colour.from_rgb(225, 0, 255))
        queue = vc.queue.copy()
        song_count = 0
        for song in queue:
            song_count += 1
            embed.add_field(name=f"{song_count}.", value=f"`{song.title}`")
        
        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def volume(self,interaction: Interaction, volume: int):
        """Changes the music volume."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        if volume < 0 or volume > 100:
            return await interaction.send("Volume must be between 0 and 100.")
        await interaction.send(f"Set the volume to {volume}%.")
        return await vc.set_volume(volume)

    @nextcord.slash_command()
    async def nowplaying(self, interaction: Interaction):
        """Returns the currently playing song"""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        else:
            vc: wavelink.Player = interaction.guild.voice_client
        
        if not vc.is_playing():
            return await interaction.send("Nothing is playing.")
        
        embed = nextcord.Embed(title=f"Now playing {vc.track.title}", description=f"Artist {vc.track.author}", color=nextcord.Colour.from_rgb(225, 0, 255))
        full_time = datetime.timedelta(seconds=vc.position)
        timestamp = full_time.split(".", 1)[0]
        embed.add_field(name="Timestamp", value=f"{str(timestamp)}")
        embed.add_field(name="Duration", value = f"{str(datetime.timedelta(seconds=vc.track.length))}")
        embed.add_field(name="Song URL", value=f"[Click Here]({str(vc.track.uri)})")

        return await interaction.send(embed=embed)
    
def setup(bot):
    bot.add_cog(Music(bot))