import nextcord, pymongo, os, re, wavelink, datetime, random, asyncio
from nextcord import Interaction
from nextcord.ext import commands, application_checks
from fuzzywuzzy import fuzz

from extra import mq_volume

#Set up our mongodb client
client = pymongo.MongoClient(os.getenv('CONN_STRING'))

#Name our access to our client database
db = client.NextcordBot

#Get all the existing collections
collections = db.list_collection_names()

#Get access to the songs collection
song_list = db['songs']

#Default player volume
default_volume = 5

#Music quiz variables
mq_status = False
mq_rounds = 10
mq_duration = 30
# mq_vol = 25
mq_leniency = 90
player_score = {}
score_embed = nextcord.Embed(title = "Music Quiz Results", color = nextcord.Colour.from_rgb(225, 0, 255))
song_indices = []
title_list = []
artist_list = []

def title_case(s):
  return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(),s)

#Function to increment player score
def increment_score(guess):
    if guess.author.name in player_score:
        player_score[str(guess.author.name)] += 1
    else:
        player_score[str(guess.author.name)] = 1

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
            host="www.exlink.ml",
            port=443,
            password="exlava",
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
    async def disconnect(self, interaction: Interaction):
        """Disconnects the bot from the voice channel."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
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
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
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
    async def music_quiz(self, interaction: Interaction):
        """Starts music quiz."""
        if mq_status is True:
            return
        mq_status = True
        #Start of game message
        await interaction.send(f"Music quiz, {mq_rounds} rounds, {mq_duration} seconds each.")
        #Join user's voice channel
        if not interaction.guild.voice_client:
            vc: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
        else:
            vc: wavelink.Player = interaction.guild.voice_client
        
        await vc.set_volume(default_volume)
        
        vc.interaction = interaction
        try:
            if vc.loop: return
        except Exception:
            setattr(vc, "loop", False)
        #Clear dictionary that stores player score
        player_dict = {}
        #Setup the embed to store game results
        score_embed.set_footer(icon_url = interaction.guild.icon_url, text = interaction.guild.name)
        #Make a list from available titles
        title_list = db["titles"]
        artist_list = db["artists"]
        #Randomize songs for as many rounds as needed
        index_list = range(0,len(title_list))
        song_indices = random.sample(index_list, mq_rounds)

        #Initialize guess flags to empty strings
        title_flag = ''
        artist_flag = ''

        #Check if user response matches the correct title
        def title_check(m):
            s1 = ''.join(e for e in m.content.lower() if e.isalnum())
            s2 = ''.join(e for e in correct_title.lower() if e.isalnum())
            percent_correct = fuzz.token_set_ratio(s1,s2)
            if percent_correct >= mq_leniency:
                increment_score(m.author.name)
                return str(m.author.name)
            return ''

        #Check if user response matches the correct artist
        def artist_check(m):
            s1 = ''.join(e for e in m.content.lower() if e.isalnum())
            s2 = ''.join(e for e in correct_artist.lower() if e.isalnum())
            percent_correct = fuzz.token_set_ratio(s1,s2)
            if percent_correct >= mq_leniency:
                increment_score(m.author.name)
                return str(m.author.name)
            return ''

        #Check if title and artist have been guessed
        def mq_check(m):
            return ((title_flag != '') and (artist_flag != ''))

        for i in range(mq_rounds):
            #Start of round
            await asyncio.sleep(3)
            await interaction.followup.send(f"Starting round {i+1}")
            #Set guess flags to false at round start
            title_flag = ''
            artist_flag = ''
            #Make the correct song the first one from our random list
            index = song_indices[i]
            correct_title = title_list[index]
            correct_artist = artist_list[index]
            #Play the song at volume
            print(f"Playing {title_list[index]} by {artist_list[index]}")
            #TODO: Make subfunctions that are shared with main music (play/volume/stop/disconnect)
            vc: wavelink.Player = interaction.guild.voice_client
            search = await wavelink.YouTubeTrack.search(
                query=f"{title_list[index]} by {artist_list[index]}", 
                return_first=True
            )
            await vc.set_volume(default_volume)
            await vc.play(search)
            try:
                #If title isn't guessed compare guess to the title
                if title_flag == '':
                    title_flag = await self.bot.wait_for('message',check=title_check)
                #If artist isn't guessed compare guess to the artist
                if artist_flag == '':
                    artist_flag = await self.bot.wait_for('message',check=artist_check)
                #End round when title and artist are guessed
                guess = await self.bot.wait_for('message',check=mq_check,timeout=mq_duration)
            except asyncio.TimeoutError:
                #Stop the round if users don't guess in time
                await vc.stop()
                await interaction.followup.send(f"Round over.\n Title: {title_case(correct_title)}\nArtist: {title_case(correct_artist)}.")
            else:
                #Stop the round and announce the round winner
                await vc.stop()
                await interaction.followup.send(f"Successfully guessed {title_case(correct_title)} by {title_case(correct_artist)}")
            #Sort player score dictionary from highest to lowest
            sorted_list = sorted(player_score.items(), key = lambda x:x[1], reverse=True)
            sorted_dict = dict(sorted_list)
            #Add each player and their score to game results embed
            for key, value in sorted_dict.items():
                score = str(value) + " pts"
                score_embed.add_field(name=key, value=score)
            #Send game results embed
            await interaction.followup.send(embed=score_embed)
            for key, value in sorted_dict.items():
                score_embed.remove_field(0)
        #Announce end of the game
        await interaction.followup.send("Music quiz is done.")
        #Sort player score dictionary from highest to lowest
        sorted_list = sorted(player_score.items(), key = lambda x:x[1], reverse=True)
        sorted_dict = dict(sorted_list)
        #Add each player and their score to game results embed
        for key, value in sorted_dict.items():
            score = str(value) + " pts"
            score_embed.add_field(name=key, value=score)
        #Send game results embed and leave voice channel
        await interaction.followup.send(embed=score_embed)
        await vc.disconnect()
        mq_status = False
        return

        
    @nextcord.slash_command()
    async def nowplaying(self, interaction: Interaction):
        """Returns the currently playing song"""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
        else:
            vc: wavelink.Player = interaction.guild.voice_client
        
        if not vc.is_playing():
            return await interaction.send("Nothing is playing.")
        
        embed = nextcord.Embed(title=f"Now playing {vc.track.title}", description=f"Artist {vc.track.author}", color=nextcord.Colour.from_rgb(225, 0, 255))
        full_time = str(datetime.timedelta(seconds=vc.position))
        timestamp = full_time.split(".", 1)[0]
        embed.add_field(name="Timestamp", value=f"{str(timestamp)}")
        embed.add_field(name="Duration", value = f"{str(datetime.timedelta(seconds=vc.track.length))}")
        embed.add_field(name="Song URL", value=f"[Click Here]({str(vc.track.uri)})")

        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def pause(self, interaction: Interaction):
        """Pauses the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.pause()
        await interaction.send("Music paused.")

    @nextcord.slash_command()
    async def play(self, interaction: Interaction, search: str):
        """Plays a song in a voice channel."""
        search = await wavelink.YouTubeTrack.search(query=search, return_first=True)
        if not interaction.guild.voice_client:
            vc: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
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
    async def queue(self, interaction: Interaction):
        """Returns songs in the queue."""
        if not interaction.guild.voice_client:
            return await interaction.send("I am not in a voice channel.")
        elif not interaction.user.voice:
            return await interaction.send("Join a voice channel first.")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
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
    async def resume(self, interaction: Interaction):
        """Resumes the current song."""
        if not interaction.guild.voice_client:
            return await interaction.send("Nothing is playing.")
        elif not getattr(interaction.user.voice, "channel", None):
            return await interaction.send("Join a voice channel first")
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
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
        elif interaction.user.voice.channel != interaction.guild.me.voice.channel:
            return await interaction.send("We have to be in the same voice channel.")
        elif mq_status is True:
            return await interaction.send("Music quiz is in progress!")
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        await vc.stop()
        await interaction.send("Music stopped.")

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
    
def setup(bot):
    bot.add_cog(Music(bot))