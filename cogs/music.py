import nextcord, pymongo, os, re, lavalink, datetime, random, asyncio
from nextcord import Interaction
from nextcord.ext import commands, application_checks
from fuzzywuzzy import fuzz

# Set up our mongodb client
client = pymongo.MongoClient(os.getenv("CONN_STRING"))

# Name our access to our client database
db = client.NextcordBot

# Get all the existing collections
collections = db.list_collection_names()

# Get access to the songs collection
song_list = db["songs"]

# Default player volume
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

url_rx = re.compile(r'https?://(?:www\.)?.+')

class LavalinkVoiceClient(nextcord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://nextcordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: nextcord.Client, channel: nextcord.abc.Connectable):
        self.client = client
        self.channel = channel
        # ensure a client already exists
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                'lavalink.botsuniversity.ml',
                443,
                'mathiscool',
                'us',
                'default-node'
            )
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()

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
        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                'lavalink.botsuniversity.ml',
                443,
                'mathiscool',
                'us',
                'default-node')  # Host, Port, Password, Region, Name
        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = ctx.command.name in ('play',)

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise commands.CommandInvokeError('Join a voicechannel first.')

        v_client = ctx.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('You need to be in my voicechannel.')

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voicechannel.
            guild_id = event.player.guild_id
            guild = self.bot.get_guild(guild_id)
            await guild.voice_client.disconnect(force=True)
    

    @nextcord.slash_command()
    async def disconnect(self, interaction: Interaction):
        """Disconnects the bot from the voice channel."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't disconnect, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not disconnect the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        player.queue.clear()
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        await interaction.voice_client.disconnect(force=True)
        await interaction.send('*⃣ | Disconnected.')

    @nextcord.slash_command()
    async def loop(self, interaction: Interaction, selection: int):
        """0 to turn off looping, 1 to loop current song, 2 to loop entire queue"""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't loop, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not loop the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        # Set the correct loop.
        await player.set_loop(selection)
        if player.loop == player.LOOP_NONE:
            await interaction.send('Loop disabled.')
        elif player.loop == player.LOOP_SINGLE:
            await interaction.send(f'Looping {player.current.title}')
        elif player.loop == player.LOOP_QUEUE:
            await interaction.send('Looping entire queue.')

    @nextcord.slash_command()
    async def music_quiz(self, interaction: Interaction):
        """Starts music quiz."""
        # Start of game message
        await interaction.send(
            f"Music quiz, {mq_rounds} rounds, {mq_duration} seconds each."
        )
        # Join user's voice channel
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        channel = interaction.user.voice.channel
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not disconnect the bot.
            return await interaction.send('You\'re not in my voicechannel!')
        await channel.connect()
        await player.set_volume(default_volume)

        # Clear dictionary that stores player score
        self.player_dict = {}
        # Setup the embed to store game results
        self.score_embed.set_footer(icon_url = interaction.guild.icon.url, text = interaction.guild.name)
        # Make a list from available titles and artists
        titles = song_list.find({}, {"title":1, "_id":0})
        artists = song_list.find({}, {"artist":1, "_id":0})
        self.title_list, self.artist_list = [], []
        for t in titles:
            self.title_list.append(t["title"])
        for a in artists:
            self.artist_list.append(a["artist"])
        print(self.title_list)
        print(self.artist_list)
        # Randomize songs for as many rounds as needed
        index_list = range(0,int(song_list.count_documents({}))+1)
        self.song_indices = random.sample(index_list, mq_rounds)
        # Enable music quiz responses to be read in the channel and store start interaction
        if self.mq_channel is None:
            self.mq_channel = interaction.channel
        else:
            return await interaction.send("Music quiz is already active in another channel! Please try again later.")
        self.mq_interaction = interaction
        # Added for testing purposes
        await interaction.send(self.player_dict)
        await interaction.send(self.score_embed)
        await interaction.send(self.title_list)
        await interaction.send(self.song_indices)

        channel = self.mq_channel

        
        async def mq_disconnect(self, interaction: Interaction):
            """Disconnects the bot from the voice channel."""
            if not interaction.voice_client:
                # We can't disconnect, if we're not connected.
                return await interaction.send('Not connected.')
            if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
                # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
                # may not disconnect the bot.
                return await interaction.send('You\'re not in my voicechannel!')

            # Clear the queue to ensure old tracks don't start playing
            # when someone else queues something.
            player.queue.clear()
            # Stop the current track so Lavalink consumes less resources.
            await player.stop()
            # Disconnect from the voice channel.
            await interaction.voice_client.disconnect(force=True)
            await interaction.send('*⃣ | Music Quiz has ended.')

        async def mq_play(self, interaction: Interaction, search: str):
            """Plays a song in a voice channel."""
            # Get the player for this guild from cache.
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)
            # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
            query = query.strip('<>')

            # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
            # SoundCloud searching is possible by prefixing "scsearch:" instead.
            if not url_rx.match(query):
                query = f'ytsearch:{query}'

            # Get the results for the query from Lavalink.
            results = await player.node.get_tracks(query)

            # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
            # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
            if not results or not results.tracks:
                return await interaction.send('Nothing found!')

            # Valid loadTypes are:
            #   TRACK_LOADED    - single video/direct URL)
            #   PLAYLIST_LOADED - direct URL to playlist)
            #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
            #   NO_MATCHES      - query yielded no results
            #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
            if results.load_type == 'PLAYLIST_LOADED':
                tracks = results.tracks
                for track in tracks:
                    # Add all of the tracks from the playlist to the queue.
                    player.add(track=track)
            else:
                track = results.tracks[0]
                player.add(track=track)

            # We don't want to call .play() if the player is playing as that will effectively skip
            # the current track.
            if not player.is_playing:
                await player.play()

        for i in range(mq_rounds):
            # Start of round
            await asyncio.sleep(3)
            await channel.send(f"Starting round {i+1}")
            # Reset guess flags for each round
            self.title_flag = ""
            self.artist_flag = ""
            # Make the correct song the first one from our random list
            index = self.song_indices[i]
            self.correct_title = self.title_list[index]
            self.correct_artist = self.artist_list[index]
            #Play the song at volume
            print("Playing " + self.title_list[index] + " by " + self.artist_list[index])
            await mq_play(self.mq_interaction, self.title_list[index]+" by "+ self.artist_list[index])
        #Announce end of the game
        await channel.send("Music quiz is done.")
        #Sort player score dictionary from highest to lowest
        sorted_list = sorted(self.player_score.items(), key = lambda x:x[1], reverse=True)
        sorted_dict = dict(sorted_list)
        # Add each player and their score to game results embed
        for key, value in sorted_dict.items():
            score = str(value) + " pts"
            self.score_embed.add_field(name=key, value=score)
        #Send game results embed and leave voice channel
        await interaction.send(embed=self.score_embed)
        await mq_disconnect(self.mq_interaction)
        self.mq_channel = None
        return
        
    @commands.Cog.listener("on_message")
    async def mq(self, message):
        # If the message is from a bot or not in an active music quiz channel, don't react
        if message.author.bot or self.mq_channel != message.channel:
            return

        channel = message.channel
        
        async def mq_stop(self, interaction: Interaction):
            """Stops the current song."""
            player = self.bot.lavalink.player_manager.get(interaction.guild.id)

            if not interaction.voice_client:
                # We can't stop, if we're not connected.
                return await interaction.send('Not connected.')
            if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
                # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
                # may not stop the bot.
                return await interaction.send('You\'re not in my voicechannel!')

            # Stop the current track so Lavalink consumes less resources.
            await player.stop()
            await interaction.send('*⃣ | Stopped playing music.')

        # Check if user response matches the correct title
        def title_check(m):
            s1 = "".join(e for e in m.content.lower() if e.isalnum())
            s2 = "".join(e for e in self.correct_title.lower() if e.isalnum())
            percent_correct = fuzz.token_set_ratio(s1, s2)
            if percent_correct >= mq_leniency:
                increment_score(m.author.name)
                return str(m.author.name)
            return ""

        # Check if user response matches the correct artist
        def artist_check(m):
            s1 = "".join(e for e in m.content.lower() if e.isalnum())
            s2 = "".join(e for e in self.correct_artist.lower() if e.isalnum())
            percent_correct = fuzz.token_set_ratio(s1, s2)
            if percent_correct >= mq_leniency:
                increment_score(m.author.name)
                return str(m.author.name)
            return ""

        # Check if title and artist have been guessed
        def mq_check(m):
            if (self.title_flag != None) and (self.artist_flag != None):
                if self.title_flag == self.artist_flag:
                    increment_score(m.author.name)
                return True
           
        try:
            # If title isn't guessed compare guess to the title
            if self.title_flag == "":
                self.title_flag = await client.wait_for("message", check=title_check)
            # If artist isn't guessed compare guess to the artist
            if self.artist_flag == "":
                self.artist_flag = await client.wait_for("message", check=artist_check)
            # End round when title and artist are guessed
            await client.wait_for("message", check=mq_check, timeout=mq_duration)
        except asyncio.TimeoutError:
            # Stop the round if users don't guess in time
            await mq_stop(self.mq_interaction)
            await channel.send(
                f"Round over.\nTitle: {title_case(self.correct_title)}\nArtist: {title_case(self.correct_artist)}."
            )
        else:
            # Stop the round and announce the round winner
            await mq_stop(self.mq_interaction)
            await channel.send(f"Successfully guessed {title_case(self.correct_title)} by {title_case(self.correct_artist)}")
            #Sort player score dictionary from highest to lowest
            sorted_list = sorted(self.player_score.items(), key = lambda x:x[1], reverse=True)
            sorted_dict = dict(sorted_list)
            # Add each player and their score to game results embed
            for key, value in sorted_dict.items():
                score = str(value) + " pts"
                self.score_embed.add_field(name=key, value=score)
            #Send game results embed
            await self.mq_interaction.send(embed=self.score_embed)
            for key, value in sorted_dict.items():
                self.score_embed.remove_field(0)

    @nextcord.slash_command()
    async def mq_swap(self, interaction: Interaction):
        """Debugging command to manually switch music quiz channel"""
        self.mq_channel = None
        await interaction.send(f"Status is {self.mq_channel}")

    @nextcord.slash_command()
    async def nowplaying(self, interaction: Interaction):
        """Returns the currently playing song"""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't get the current song, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not query the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        if not player.is_playing():
            return await interaction.send("Nothing is playing.")

        embed = nextcord.Embed(
            title=f"Now playing: {player.current.title}",
            description=f"Artist: {player.current.author}",
            color=nextcord.Colour.from_rgb(225, 0, 255),
        )
        embed.add_field(
            name="Duration", value=f"{str(datetime.timedelta(seconds=player.current.duration))}"
        )
        embed.add_field(name="Song URL", value=f"[Click Here]({str(player.current.uri)})")

        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def pause(self, interaction: Interaction):
        """Pauses the current song."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't pause, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not pause the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        # Pause the current track.
        await player.set_pause(True)
        await interaction.send(f'*⃣ | Paused {player.current.title}.')

    @nextcord.slash_command()
    async def play(self, interaction: Interaction,*, search: str):
        """Plays a song in a voice channel."""
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
        if not results or not results.tracks:
            return await interaction.send('Nothing found!')

        embed = nextcord.Embed(color=nextcord.Colour.from_rgb(225, 0, 255))

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results.load_type == 'PLAYLIST_LOADED':
            tracks = results.tracks

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=interaction.author.id, track=track)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
        else:
            track = results.tracks[0]
            embed.title = 'Track Enqueued'
            embed.description = f'[{track.title}]({track.uri})'

            player.add(requester=interaction.author.id, track=track)

        await interaction.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @nextcord.slash_command()
    async def queue(self, interaction: Interaction):
        """Returns songs in the queue."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't get the queue, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not query the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        if not player.queue:
            return await interaction.send("Queue is empty.")

        embed = nextcord.Embed(
            title="Queue", color=nextcord.Colour.from_rgb(225, 0, 255)
        )
        queue = player.queue
        song_count = 0
        for song in queue:
            song_count += 1
            embed.add_field(name=f"{song_count}.", value=f"`{song.title}`")

        return await interaction.send(embed=embed)

    @nextcord.slash_command()
    async def resume(self, interaction: Interaction):
        """Resumes the current song."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't resume, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not resume the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        # Resume the current track.
        await player.set_pause(False)
        await interaction.send(f'*⃣ | Resumed {player.current.title}.')

    @nextcord.slash_command()
    async def skip(self, interaction: Interaction):
        """Skips the current song."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't skip, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not skip the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        # Skip the current track.
        await player.skip()
        await interaction.send('*⃣ | Stopped playing music.')

    @nextcord.slash_command()
    async def stop(self, interaction: Interaction):
        """Stops the current song."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't stop, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not stop the bot.
            return await interaction.send('You\'re not in my voicechannel!')

        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        await interaction.send('*⃣ | Stopped playing music.')

    @nextcord.slash_command()
    async def volume(self, interaction: Interaction, volume: int):
        """Changes the music volume."""
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        if not interaction.voice_client:
            # We can't change volume, if we're not connected.
            return await interaction.send('Not connected.')
        if not interaction.author.voice or (player.is_connected and interaction.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not change the bot's volume.
            return await interaction.send('You\'re not in my voicechannel!')

        # Set the new volume:
        if volume < 0 or volume > 100:
            return await interaction.send("Volume must be between 0 and 100.")
        await player.set_volume(volume)
        await interaction.send(f'*⃣ | Set volume to {volume}%.')


def setup(bot):
    bot.add_cog(Music(bot))
