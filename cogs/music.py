import nextcord, pymongo, os, json, wavelink as nextwave, re, math, datetime, random, asyncio
from nextcord import Interaction
from nextcord.ext import commands, application_checks
from fuzzywuzzy import fuzz

# Set up our mongodb client
client = pymongo.MongoClient(os.getenv("CONN_STRING"))

# Get our bot ID for later use
bot_ID = os.getenv("CLIENT_ID")

# Name our access to our client database
db = client.NextcordBot

# Get all the existing collections
collections = db.list_collection_names()

# Get access to the songs collection
song_list = db["songs"]

# Default player volume and song queue
default_volume = 5

# Music quiz variables
mq_rounds = 10
mq_duration = 30
mq_leniency = 90
player_score = {}
score_embed = nextcord.Embed(
    title="Music Quiz Results", color=nextcord.Colour.from_rgb(225, 0, 255)
)
song_indices = []
title_list = []
artist_list = []

def title_case(s):
    return re.sub(
        r"[A-Za-z]+('[A-Za-z]+)?",
        lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(),
        s,
    )

# Function to increment player score
def increment_score(guess):
    if guess.author.name in player_score:
        player_score[str(guess.author.name)] += 1
    else:
        player_score[str(guess.author.name)] = 1


# Function to do fuzzy string matching
def fuzz_check(s1, s2):
    return (
        fuzz.token_set_ratio(
            "".join(e for e in s1.content.lower() if e.isalnum()),
            "".join(e for e in s2.lower() if e.isalnum()),
        )
        >= mq_leniency
    )

class Music_Buttons(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=math.inf)
        self.value = None

    @nextcord.ui.button(label = "⏯️-Play/Pause", style = nextcord.ButtonStyle.blurple)
    async def pause(self, button : nextcord.ui.Button, interaction : nextcord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("Please join the voice channel!", ephemeral=True)
        elif not interaction.user.voice:
            return await interaction.response.send_message("Please join the voice channel!", ephemeral=True)
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("I am not connected to voice!", ephemeral=True)
        vc: nextwave.Player = interaction.guild.voice_client
        if vc.is_paused():
            await vc.resume()
            return await interaction.response.send_message(f"**{vc.track.title}** is now playing!", ephemeral=True)
        await vc.pause()
        await interaction.response.send_message(f"**{vc.track.title}** is now paused!", ephemeral=True)

    @nextcord.ui.button(label="⏭️-Skip", style=nextcord.ButtonStyle.blurple)
    async def skip(self, button: nextcord.ui.Button, interaction:nextcord.Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: nextwave.Player = interaction.guild.voice_client
        try:
            next_song = vc.queue.get()
            await vc.play(next_song)
            return await interaction.response.send_message(f"**{vc.track.title}** was skipped! Now playing: {next_song}", ephemeral=True)
        except:
            return await interaction.response.send_message(f"Queue is empty!", ephemeral=True)
    
    @nextcord.ui.button(label = "🔁-Queue", style = nextcord.ButtonStyle.green)
    async def queue(self, button : nextcord.ui.Button, interaction : nextcord.Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: nextwave.Player = interaction.guild.voice_client
        if vc.queue.is_empty:
            return await interaction.send("Queue is empty!")
        queue = vc.queue.copy()
        song_count = 0
        msg = ""
        for song in queue:
            song_count += 1
            msg += f"**{song_count}**: **{song.title}**\n"
        return await interaction.response.send_message(f"__Queue__\n{msg}", ephemeral=True)

    @nextcord.ui.button(label = "🔁-Loop", style = nextcord.ButtonStyle.green)
    async def loop(self, button : nextcord.ui.Button, interaction : nextcord.Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: nextwave.Player = interaction.guild.voice_client
        if not vc.loop:
            vc.loop ^= True
            await interaction.response.send_message(f"**{vc.track.title}** is now looping!", ephemeral=True)
        else:
            setattr(vc, "loop", False)
            vc.loop ^= True
            await interaction.response.send_message(f"**{vc.track.title}** is no longer looping!", ephemeral=True)
        
        self.value = True
    
    @nextcord.ui.button(label = "⏹️-Stop", style = nextcord.ButtonStyle.red)
    async def disconnect(self, button : nextcord.ui.Button, interaction : nextcord.Interaction):
        try:
            if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
                return await interaction.response.send_message("We must be in the same voice channel!", ephemeral=True)
        except:
            return await interaction.response.send_message("You or I am not in the voice channel!", ephemeral=True)
        vc: nextwave.Player = interaction.guild.voice_client
        await vc.disconnect()
        await interaction.response.send_message(f"I have left the voice channel!", ephemeral=True)
        self.value = True

# TODO: Fix music quiz functionality
class Music(commands.Cog, name="Music"):
    """Commands for playing music in voice channels"""

    COG_EMOJI = "🎵"

    def __init__(self, bot):
        self.bot = bot
        self.mq_channel = None
        self.mq_interaction = None
        self.song_indices = []
        self.player_dict = {}
        self.player_score = {}
        self.title_list = []
        self.artist_list = []
        self.title_flag = None
        self.artist_flag = None
        self.correct_title = None
        self.correct_artist = None
        self.score_embed = nextcord.Embed(title = "Music Quiz Results", color = nextcord.Colour.from_rgb(225, 0, 255))    

    async def node_connect(self):
        await self.bot.wait_until_ready()
        await nextwave.NodePool.create_node(bot=self.bot, host='lavalink.botsuniversity.ml', port=443, password='mathiscool', https=True)

    @commands.Cog.listener()
    async def on_ready(self):   
        self.bot.loop.create_task(Music.node_connect(self))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == bot_ID and before.channel is not None and after.channel is None:
            vc: nextwave.Player = member.guild.voice_client
            vc.queue.clear()
            await vc.disconnect()
    
    @nextcord.slash_command()
    async def play(self, interaction: Interaction, song: str):
        view = Music_Buttons()
        search = await nextwave.YouTubeTrack.search(query=song, return_first=True)
        text = search.title
        if not interaction.guild.voice_client:
            vc : nextwave.Player = await interaction.user.voice.channel.connect(cls=nextwave.Player)
        elif not interaction.user.voice:
            return await interaction.send("Please enter a voice channel!")
        else:
            vc: nextwave.Player = interaction.guild.voice_client
        if vc.queue.is_empty and not vc.is_playing():
            await vc.play(search)
            embed = nextcord.Embed(title=f"Added {text} to the queue!",
            color=nextcord.Colour.from_rgb(225, 0, 255))
            await interaction.send(embed=embed, view=view)
            await view.wait()
        else:
            await vc.queue.put_wait(search)
            embed = nextcord.Embed(title=f"Added {text} to the queue!",
            color=nextcord.Colour.from_rgb(225, 0, 255))
            msg = await interaction.send(embed=embed)
        vc.interaction = interaction
        try:
            setattr(vc, "loop", False)
        except:
            setattr(vc, "loop", False)

    @commands.Cog.listener() 
    async def on_wavelink_track_end(player: nextwave.Player, track: nextwave.Track, reason):
        vc: player = player
        if vc.loop:
            return await vc.play(track)
        elif vc.queue.is_empty:
            return await vc.disconnect()
        next_song = vc.queue.get()
        await vc.play(next_song)

    # @nextcord.slash_command()
    # async def music_quiz(self, interaction: Interaction):
    #     """Starts music quiz."""
    #     # Start of game message
    #     await interaction.send(
    #         f"Music quiz, {mq_rounds} rounds, {mq_duration} seconds each."
    #     )
    #     # Join user's voice channel
    #     player = self.bot.lavalink.player_manager.get(interaction.guild.id)
    #     channel = interaction.user.voice.channel
    #     if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
    #         # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
    #         # may not disconnect the bot.
    #         return await interaction.send('You\'re not in my voicechannel!')
    #     await channel.connect()
    #     await player.set_volume(default_volume)

    #     # Clear dictionary that stores player score
    #     self.player_dict = {}
    #     # Setup the embed to store game results
    #     self.score_embed.set_footer(icon_url = interaction.guild.icon.url, text = interaction.guild.name)
    #     # Make a list from available titles and artists
    #     titles = song_list.find({}, {"title":1, "_id":0})
    #     artists = song_list.find({}, {"artist":1, "_id":0})
    #     self.title_list, self.artist_list = [], []
    #     for t in titles:
    #         self.title_list.append(t["title"])
    #     for a in artists:
    #         self.artist_list.append(a["artist"])
    #     print(self.title_list)
    #     print(self.artist_list)
    #     # Randomize songs for as many rounds as needed
    #     index_list = range(0,int(song_list.count_documents({}))+1)
    #     self.song_indices = random.sample(index_list, mq_rounds)
    #     # Enable music quiz responses to be read in the channel and store start interaction
    #     if self.mq_channel is None:
    #         self.mq_channel = interaction.channel
    #     else:
    #         return await interaction.send("Music quiz is already active in another channel! Please try again later.")
    #     self.mq_interaction = interaction
    #     # Added for testing purposes
    #     await interaction.send(self.player_dict)
    #     await interaction.send(self.score_embed)
    #     await interaction.send(self.title_list)
    #     await interaction.send(self.song_indices)

    #     channel = self.mq_channel

        
    #     async def mq_disconnect(self, interaction: Interaction):
    #         """Disconnects the bot from the voice channel."""
    #         if not interaction.voice_client:
    #             # We can't disconnect, if we're not connected.
    #             return await interaction.send('Not connected.')
    #         if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
    #             # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
    #             # may not disconnect the bot.
    #             return await interaction.send('You\'re not in my voicechannel!')

    #         # Clear the queue to ensure old tracks don't start playing
    #         # when someone else queues something.
    #         player.queue.clear()
    #         # Stop the current track so Lavalink consumes less resources.
    #         await player.stop()
    #         # Disconnect from the voice channel.
    #         await interaction.voice_client.disconnect(force=True)
    #         await interaction.send('*⃣ | Music Quiz has ended.')

    #     async def mq_play(self, interaction: Interaction, search: str):
    #         """Plays a song in a voice channel."""
    #         # Get the player for this guild from cache.
    #         player = self.bot.lavalink.player_manager.get(interaction.guild.id)
    #         # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
    #         query = query.strip('<>')

    #         # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
    #         # SoundCloud searching is possible by prefixing "scsearch:" instead.
    #         if not url_rx.match(query):
    #             query = f'ytsearch:{query}'

    #         # Get the results for the query from Lavalink.
    #         results = await player.node.get_tracks(query)

    #         # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    #         # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
    #         if not results or not results.tracks:
    #             return await interaction.send('Nothing found!')

    #         # Valid loadTypes are:
    #         #   TRACK_LOADED    - single video/direct URL)
    #         #   PLAYLIST_LOADED - direct URL to playlist)
    #         #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #         #   NO_MATCHES      - query yielded no results
    #         #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    #         if results.load_type == 'PLAYLIST_LOADED':
    #             tracks = results.tracks
    #             for track in tracks:
    #                 # Add all of the tracks from the playlist to the queue.
    #                 player.add(track=track)
    #         else:
    #             track = results.tracks[0]
    #             player.add(track=track)

    #         # We don't want to call .play() if the player is playing as that will effectively skip
    #         # the current track.
    #         if not player.is_playing:
    #             await player.play()

    #     for i in range(mq_rounds):
    #         # Start of round
    #         await asyncio.sleep(3)
    #         await channel.send(f"Starting round {i+1}")
    #         # Reset guess flags for each round
    #         self.title_flag = ""
    #         self.artist_flag = ""
    #         # Make the correct song the first one from our random list
    #         index = self.song_indices[i]
    #         self.correct_title = self.title_list[index]
    #         self.correct_artist = self.artist_list[index]
    #         #Play the song at volume
    #         print("Playing " + self.title_list[index] + " by " + self.artist_list[index])
    #         await mq_play(self.mq_interaction, self.title_list[index]+" by "+ self.artist_list[index])
    #     #Announce end of the game
    #     await channel.send("Music quiz is done.")
    #     #Sort player score dictionary from highest to lowest
    #     sorted_list = sorted(self.player_score.items(), key = lambda x:x[1], reverse=True)
    #     sorted_dict = dict(sorted_list)
    #     # Add each player and their score to game results embed
    #     for key, value in sorted_dict.items():
    #         score = str(value) + " pts"
    #         self.score_embed.add_field(name=key, value=score)
    #     #Send game results embed and leave voice channel
    #     await interaction.send(embed=self.score_embed)
    #     await disconnect(self.mq_interaction)
    #     self.mq_channel = None
    #     return
        
    # @commands.Cog.listener("on_message")
    # async def mq(self, message):
    #     # If the message is from a bot or not in an active music quiz channel, don't react
    #     if message.author.bot or self.mq_channel != message.channel:
    #         return

    #     channel = message.channel
        
    #     async def mq_stop(self, interaction: Interaction):
    #         """Stops the current song."""
    #         player = self.bot.lavalink.player_manager.get(interaction.guild.id)

    #         if not interaction.voice_client:
    #             # We can't stop, if we're not connected.
    #             return await interaction.send('Not connected.')
    #         if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
    #             # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
    #             # may not stop the bot.
    #             return await interaction.send('You\'re not in my voicechannel!')

    #         # Stop the current track so Lavalink consumes less resources.
    #         await player.stop()
    #         await interaction.send('*⃣ | Stopped playing music.')

    #     # Check if user response matches the correct title
    #     def title_check(m):
    #         s1 = "".join(e for e in m.content.lower() if e.isalnum())
    #         s2 = "".join(e for e in self.correct_title.lower() if e.isalnum())
    #         percent_correct = fuzz.token_set_ratio(s1, s2)
    #         if percent_correct >= mq_leniency:
    #             increment_score(m.author.name)
    #             return str(m.author.name)
    #         return ""

    #     # Check if user response matches the correct artist
    #     def artist_check(m):
    #         s1 = "".join(e for e in m.content.lower() if e.isalnum())
    #         s2 = "".join(e for e in self.correct_artist.lower() if e.isalnum())
    #         percent_correct = fuzz.token_set_ratio(s1, s2)
    #         if percent_correct >= mq_leniency:
    #             increment_score(m.author.name)
    #             return str(m.author.name)
    #         return ""

    #     # Check if title and artist have been guessed
    #     def mq_check(m):
    #         if (self.title_flag != None) and (self.artist_flag != None):
    #             if self.title_flag == self.artist_flag:
    #                 increment_score(m.author.name)
    #             return True
           
    #     try:
    #         # If title isn't guessed compare guess to the title
    #         if self.title_flag == "":
    #             self.title_flag = await client.wait_for("message", check=title_check)
    #         # If artist isn't guessed compare guess to the artist
    #         if self.artist_flag == "":
    #             self.artist_flag = await client.wait_for("message", check=artist_check)
    #         # End round when title and artist are guessed
    #         await client.wait_for("message", check=mq_check, timeout=mq_duration)
    #     except asyncio.TimeoutError:
    #         # Stop the round if users don't guess in time
    #         await mq_stop(self.mq_interaction)
    #         await channel.send(
    #             f"Round over.\nTitle: {title_case(self.correct_title)}\nArtist: {title_case(self.correct_artist)}."
    #         )
    #     else:
    #         # Stop the round and announce the round winner
    #         await mq_stop(self.mq_interaction)
    #         await channel.send(f"Successfully guessed {title_case(self.correct_title)} by {title_case(self.correct_artist)}")
    #         #Sort player score dictionary from highest to lowest
    #         sorted_list = sorted(self.player_score.items(), key = lambda x:x[1], reverse=True)
    #         sorted_dict = dict(sorted_list)
    #         # Add each player and their score to game results embed
    #         for key, value in sorted_dict.items():
    #             score = str(value) + " pts"
    #             self.score_embed.add_field(name=key, value=score)
    #         #Send game results embed
    #         await self.mq_interaction.send(embed=self.score_embed)
    #         for key, value in sorted_dict.items():
    #             self.score_embed.remove_field(0)

    # @nextcord.slash_command()
    # async def mq_swap(self, interaction: Interaction):
    #     """Debugging command to manually switch music quiz channel"""
    #     self.mq_channel = None
    #     await interaction.send(f"Status is {self.mq_channel}")

    

def setup(bot):
    bot.add_cog(Music(bot))
