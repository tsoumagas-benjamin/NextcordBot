import nextcord, NextcordUtils, pymongo, os, re
from nextcord.ext import commands

#Name our access to the music library
music = NextcordUtils.Music()

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

class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot

    #TODO: Implement music quiz functionality
        
    @commands.command(aliases=['as'])
    async def addsong(self, ctx, *, song):
        """Adds a song to the music quiz playlist
        
        Example: `$addsong Africa, Toto`"""
        title, artist = song.split(", ",2)
        title = title_case(title)
        artist = title_case(artist)
        input = {"title":title, "artist":artist}
        song_list.insert_one(input)
        await ctx.send(f"Added {title} by {artist}")

    @commands.command(aliases=['ds'])
    async def deletesong(self, ctx, *, song):
        """Deletes a song from the music quiz playlist
        
        Example: `$deletesong Africa, Toto`"""
        title, artist = song.split(", ",2)
        title = title_case(title)
        artist = title_case(artist)
        input = {"title":title, "artist":artist}
        song_list.delete_one(input)
        await ctx.send(f"Deleted {title} by {artist}")

    @commands.command()
    async def songs(self, ctx):
        """Gets all songs available for music quiz
        
        Example: `$songs`"""
        embed = nextcord.Embed(title="Songs", description="Songs that will appear in music quiz.", color=nextcord.Colour.blurple())
        song_cursor = song_list.find({}, {"_id":0, "title":1, "artist":1})
        for song in song_cursor:
            embed.add_field(name=f"{song['title']}", value=f"{song['artist']}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['rs'])
    async def randomsong(self, ctx):
        """Gets a random song from the music quiz playlist
        
        Example: `$randomsong`"""
        object = song_list.aggregate([{ "$sample": { "size": 1 }}])
        for x in object:
            title, artist = x['title'], x['artist']
        await ctx.send(f"{title} by {artist}")
        
    @commands.command()
    async def join(self, ctx):
        """Get the bot to join a voice channel
        
        Example: `$join`"""
        await ctx.author.voice.channel.connect() #Joins author's voice channel
        
    @commands.command()
    async def leave(self, ctx):
        """Get the bot to leave a voice channel
        
        Example: `$leave`"""
        await ctx.voice_client.disconnect()
        
    @commands.command()
    async def play(self, ctx, *, url):
        """Get the bot to play a song from a url
        
        Example: `$play https://youtu.be/dQw4w9WgXcQ"""
        player = music.get_player(guild_id=ctx.guild.id)
        if not player:
            player = music.create_player(ctx, ffmpeg_error_betterfix=True)
        if not ctx.voice_client.is_playing():
            await player.queue(url, search=True)
            song = await player.play()
            await ctx.send(f"Playing {song.name}")
        else:
            song = await player.queue(url, search=True)
            await ctx.send(f"Queued {song.name}")     
    @commands.command()
    async def pause(self, ctx):
        """Get the bot to pause the music
        
        Example: `$pause`"""
        player = music.get_player(guild_id=ctx.guild.id)
        song = await player.pause()
        await ctx.send(f"Paused {song.name}")
        
    @commands.command()
    async def resume(self, ctx):
        """Get the bot to resume the music
        
        Example: `$resume`"""
        player = music.get_player(guild_id=ctx.guild.id)
        song = await player.resume()
        await ctx.send(f"Resumed {song.name}")
        
    @commands.command()
    async def stop(self, ctx):
        """Get the bot to stop the music and leave the voice channel
        
        Example: `$stop`"""
        player = music.get_player(guild_id=ctx.guild.id)
        await player.stop()
        await ctx.send("Stopped")
        
    @commands.command()
    async def loop(self, ctx):
        """Get the bot to loop the current song
        
        Example: `$loop`"""
        player = music.get_player(guild_id=ctx.guild.id)
        song = await player.toggle_song_loop()
        if song.is_looping:
            await ctx.send(f"Enabled loop for {song.name}")
        else:
            await ctx.send(f"Disabled loop for {song.name}")
        
    @commands.command()
    async def queue(self, ctx):
        """Show all the songs currently queued to play in open
        
        Example: `$queue`"""
        player = music.get_player(guild_id=ctx.guild.id)
        await ctx.send(f"{', '.join([song.name for song in player.current_queue()])}")
        
    @commands.command()
    async def np(self, ctx):
        """Get information on the song currently Playing
        
        Example: `$np`"""
        player = music.get_player(guild_id=ctx.guild.id)
        song = player.now_playing()
        await ctx.send(song.name)
        
    @commands.command()
    async def skip(self, ctx):
        """Skip the currently playing song
        
        Example: `$skip`"""
        player = music.get_player(guild_id=ctx.guild.id)
        data = await player.skip(force=True)
        if len(data) == 2:
            await ctx.send(f"Skipped from {data[0].name} to {data[1].name}")
        else:
            await ctx.send(f"Skipped {data[0].name}")

    @commands.command()
    async def volume(self, ctx, vol):
        """Changes the bot's volume (0-100)
        
        Example: `$volume 25`"""
        player = music.get_player(guild_id=ctx.guild.id)
        song, volume = await player.change_volume(float(vol) / 100) # volume should be a float between 0 to 1
        await ctx.send(f"Changed volume for {song.name} to {volume*100}%")
        
    @commands.command()
    async def remove(self, ctx, index):
        """Removes a song at a specified index
        
        Example: `$remove 3`"""
        player = music.get_player(guild_id=ctx.guild.id)
        song = await player.remove_from_queue(int(index))
        await ctx.send(f"Removed {song.name} from queue")
    

def setup(bot):
    bot.add_cog(Music(bot))