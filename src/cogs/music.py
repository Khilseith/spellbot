import re
from typing import List, Optional

import discord
import lavalink
from discord import app_commands
from discord.ext import commands
from fuzzywuzzy import fuzz, process
from lavalink.client import asyncio

from utils.paginator import Paginator

url_rx = re.compile(r"https?://(?:www\.)?.+")


class MusicError(discord.DiscordException):
    """Custom Error for music commands"""


class LavalinkVoiceClient(discord.VoiceClient):
    """Voice Client used for lavalink

    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel  # type: ignore
        # ensure a client already exists
        if hasattr(self.client, "lavalink"):
            self.lavalink = self.client.lavalink  # type: ignore
        else:
            self.client.lavalink = lavalink.Client(client.user.id)  # type: ignore
            self.client.lavalink.add_node(  # type: ignore
                "localhost", 2333, "Th3Pa$$wordToPa$$Th!s!", "us", "default-node"
            )
            self.lavalink = self.client.lavalink  # type: ignore

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {"t": "VOICE_SERVER_UPDATE", "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {"t": "VOICE_STATE_UPDATE", "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

        channel_id = data["channel_id"]

        if channel_id is None:
            self.destroy_me = True
            await self.disconnect()
        elif channel_id != self.channel.id:
            self.channel = self.client.get_channel(int(channel_id))  # type: ignore

    async def connect(
        self,
        *,
        timeout: float,
        reconnect: bool,
        self_deaf: bool = False,
        self_mute: bool = False,
    ) -> None:
        """Connect VoiceClient to Channel

        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(
            channel=self.channel, self_mute=self_mute, self_deaf=self_deaf
        )

    async def disconnect(self, *, force: bool = False) -> None:
        """Disconnect the VoiceClient from the channel

        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)
        if player is None:
            return

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)
        player.queue.clear()
        player.set_loop(0)
        player.set_shuffle(False)
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()


class Music(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

        if not hasattr(client, "lavalink"):
            setattr(client, "lavalink", lavalink.Client(client.user.id))  # type: ignore
            # Host, Port, Password, Region, Name
            clientLavalink = getattr(client, "lavalink")
            clientLavalink.add_node(
                "localhost", 2333, "Th3Pa$$wordToPa$$Th!s!", "us", "default-node"
            )

        lavalink.add_event_hook(self.track_hook)

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voicechannel.
            event.player.set_loop(0)
            event.player.set_shuffle(False)
            guild_id = int(event.player.guild_id)
            guild = self.client.get_guild(guild_id)
            if guild and guild.voice_client:
                await guild.voice_client.disconnect(force=True)

    async def ensure_voice(self, interaction: discord.Interaction):
        """This check ensures that the bot and command author are in the same voicechannel."""
        player = self.client.lavalink.player_manager.create(interaction.guild.id)  # type: ignore
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc do not require the bot to be in a voicechannel so don't need listing here.
        should_connect = True
        if not interaction.user.voice or not interaction.user.voice.channel:  # type: ignore
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise MusicError("Join a voicechannel first.")

        v_client = interaction.guild.voice_client  # type: ignore
        if getattr(v_client, "destroy_me", False):
            await interaction.guild.voice_client.disconnect(force=True)  # type: ignore
            v_client = None  # type: ignore
        if not v_client:
            if not should_connect:
                raise MusicError("Not connected.")

            permissions = interaction.user.voice.channel.permissions_for(  # type: ignore
                interaction.guild.get_member(self.client.user.id)  # type: ignore
            )

            if (
                not permissions.connect or not permissions.speak
            ):  # Check user limit too?
                raise MusicError("I need the `CONNECT` and `SPEAK` permissions.")

            player.store("channel", interaction.channel.id)  # type: ignore
            await interaction.user.voice.channel.connect(cls=LavalinkVoiceClient)  # type: ignore
        else:
            if v_client.channel.id != interaction.user.voice.channel.id:  # type: ignore
                raise MusicError("You need to be in my voicechannel.")

    @app_commands.command(name="play", description="Play a song in voice chat")
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, query: str):
        """Searches and plays a song from a given query."""
        await self.ensure_voice(interaction)

        # Get the player for this guild from cache.
        player = self.client.lavalink.player_manager.get(interaction.guild.id)  # type: ignore
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f"ytsearch:{query}"

        # Get the results for the query from Lavalink.
        results: lavalink.LoadResult = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # ALternatively, resullts.tracks could be an empty array if the query yielded no tracks.
        if not results or not results.tracks:
            return await interaction.response.send_message(
                "Nothing found!", ephemeral=True
            )

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results.load_type == "PLAYLIST_LOADED":
            tracks = results.tracks

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=interaction.user.id, track=track)

            embed.title = "Playlist Enqueued!"
            embed.description = (
                f"[{results.playlist_info.name}]({query}) - {len(tracks)} tracks"
            )
        else:
            track: lavalink.AudioTrack = results.tracks[0]
            embed.title = "Track Enqueued"
            embed.description = f"[{track.title}]({track.uri})"
            # check if track is a stream, give appropriate track length
            tracklength = (
                "LIVE" if track.stream else lavalink.format_time(track.duration)
            )

            embed.add_field(name="Length:", value=tracklength, inline=False)
            embed.add_field(name="Author:", value=track.author, inline=False)

            player.add(requester=interaction.user.id, track=track)

        await interaction.response.send_message(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @app_commands.command(
        name="disconnect",
        description="Makes the bot leave the voice channel and stops the queue.",
    )
    @app_commands.guild_only()
    async def disconnect(self, interaction: discord.Interaction):
        """Disconnects the player from the voice channel and clears its queue."""
        await self.ensure_voice(interaction)

        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            # We can't disconnect, if we're not connected.
            return await interaction.response.send_message(
                "Not connected.", ephemeral=True
            )
        if not interaction.user.voice or (  # type: ignore
            player.is_connected
            and interaction.user.voice.channel.id != int(player.channel_id)  # type: ignore
        ):
            return await interaction.response.send_message(
                "You're not in my voicechannel!"
            )

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        player.queue.clear()
        player.set_loop(0)
        player.set_shuffle(False)
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        await interaction.guild.voice_client.disconnect(force=True)  # type: ignore
        await interaction.response.send_message("*⃣ | Disconnected.")

    @app_commands.command(name="queue", description="Display the bot's current queue")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction):
        await self.ensure_voice(interaction)

        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return await interaction.response.send_message(
                "Not connected!", ephemeral=True
            )

        q = player.queue

        # check shuffle/loop status
        if player.shuffle:
            shuffle = "✔"
        if player.repeat:
            repeat = "queue" if player.repeat == 2 else "song"
        if not player.shuffle:
            shuffle = "❌"
        if not player.repeat:
            repeat = "❌"
        # check if pagination is required
        if len(q) > 10:

            embeds = []

            # func that checks if 'a' is a multiple of b if not rounds up to the nearest
            def round_up_nearest(a, b):
                return a + b - (a % b) if a % b else a

            # rounds the amount of songs up to a multiple of 10
            times = round_up_nearest(len(q), 10)

            times = times // 10  # divides it by 10 telling us how many pages we need

            tracknum = 0  # tracks what track we are on
            for x, _ in enumerate(range(times)):  # for the pages we need create pages

                # create the page template
                embed = discord.Embed(title="Queue", color=discord.Color.blurple())
                embed.set_footer(
                    text=f"Shuffle: {shuffle} Loop: {repeat} Page {x + 1}/{times}"  # type: ignore
                )

                for y, track in enumerate(
                    q[10 * x :]  # flake8: ignore
                ):  # create the page slicing out the songs already added

                    tracknum += 1

                    # Check if it is live
                    tracklength = (
                        "LIVE" if track.stream else lavalink.format_time(track.duration)
                    )
                    embed.add_field(
                        name=f"Track {tracknum}:",
                        value=f"[{track.title}]({track.uri})\nLength: {tracklength}",
                        inline=False,
                    )

                    # make sure each page has only 10 songs
                    if (y + 1) == 10:
                        break

                embeds.append(embed)  # add the page

            await interaction.response.send_message(
                embed=embeds[0], view=Paginator(embeds)
            )  # send page 1

        else:  # no paganation queue

            embed = discord.Embed(title="Queue")  # make embed

            if q != []:  # if queue not empty

                embed.color = discord.Color.blurple()

                for x, track in enumerate(q):  # loop for each track
                    track: lavalink.AudioTrack

                    # get track length
                    tracklength = (
                        "LIVE" if track.stream else lavalink.format_time(track.duration)
                    )

                    embed.add_field(
                        name=f"Track {x + 1}:",
                        value=f"[{track.title}]({track.uri})\nLength: {tracklength}",
                        inline=False,
                    )

            else:
                embed.description = "Queue is currently empty!"
                embed.color = discord.Color.red()

            embed.set_footer(text=f"Shuffle: {shuffle} Loop: {repeat}")  # type: ignore
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Skips the current track")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        await self.ensure_voice(interaction)

        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        if player.current is None:
            return await interaction.response.send_message(
                "No current track", ephemeral=True
            )

        embed = discord.Embed(title="Skipping:", description=player.current.title)
        embed.color = 0x8F4545

        ephemeral = False

        try:
            if player.queue != []:
                condition = True
            else:
                condition = False

            await player.skip()

            if condition:
                np = player.current

                tracklength = (
                    "LIVE"
                    if player.current.stream
                    else lavalink.format_time(player.current.duration)
                )

                embed.add_field(
                    name="Now Playing:",
                    value=f"[{np.title}]({np.uri})\nLength: {tracklength}\nAuthor: {np.author}",
                )

        except Exception:
            ephemeral = True
            embed = discord.Embed(title="Error!", description="Problem Skipping Track.")

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(
        name="nowplaying", description="Display the song currently playing"
    )
    async def nowplaying(self, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        if not player.current:
            return await interaction.response.send_message(
                "No song currently playing!", ephemeral=True
            )

        tracklength = (
            "LIVE"
            if player.current.stream
            else lavalink.format_time(player.current.duration)
        )
        currentTime = (
            "LIVE"
            if player.current.stream
            else f"{lavalink.format_time(int(player.position))}/{tracklength}"
        )
        embed = discord.Embed(title="Now Playing:")
        embed.description = f"[{player.current.title}]({player.current.uri})"
        embed.add_field(name="Author", value=player.current.author, inline=False)
        embed.add_field(name="Current Time:", value=currentTime, inline=False)
        embed.color = discord.Color.purple()

        # check shuffle/loop status
        if player.shuffle:
            shuffle = "✔"
        if player.repeat:
            repeat = "queue" if player.repeat == 2 else "song"
        if not player.shuffle:
            shuffle = "❌"
        if not player.repeat:
            repeat = "❌"

        embed.set_footer(text=f"Shuffle: {shuffle} Loop: {repeat}")  # type: ignore
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loop", description="Make the song/queue loop")
    @app_commands.guild_only()
    async def loop(self, interaction: discord.Interaction, type: Optional[str] = None):
        await self.ensure_voice(interaction)
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        loop = ""

        if type is not None:
            match type.lower():
                case "queue":
                    loop = "queue"
                case "song":
                    loop = "song"
                case _:
                    if player.loop:
                        loop = "off"
                    else:
                        loop = "queue"
        else:
            if player.loop:
                loop = "off"
            else:
                loop = "queue"

        embed = discord.Embed(
            title="Changing Loop", description=f"Setting loop to `{loop}`"
        )
        embed.color = discord.Color.blurple()

        match loop:
            case "queue":
                loop = 2
            case "song":
                loop = 1
            case "off":
                loop = 0

        player.set_loop(loop)
        await interaction.response.send_message(embed=embed)

    @loop.autocomplete("type")
    async def loop_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        options = ["song", "queue", "off"]
        for i in options:
            if any([current.startswith(i[:y]) for y in range(1, len(i) + 1)]):
                return [app_commands.Choice(name=i, value=i)]

        return [app_commands.Choice(name=option, value=option) for option in options]

    @app_commands.command(name="clear", description="Clears the current queue")
    @app_commands.guild_only()
    async def clear(self, interaction: discord.Interaction):
        await self.ensure_voice(interaction)
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        embed = discord.Embed()
        ephemeral = False

        if player.queue != []:
            embed.title = "Clearing Queue"
            embed.description = "💥 Queue Cleared"
            player.queue.clear()
        elif player.queue == []:
            ephemeral = True
            embed.title = "Clearing queue"
            embed.description = "Nothing to clear."

        embed.color = discord.Color.blurple()
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(name="pause", description="Pauses the current song")
    @app_commands.guild_only()
    async def pause(self, interaction: discord.Interaction):
        await self.ensure_voice(interaction)
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        embed = discord.Embed(
            title="Un-Pausing" if player.paused else "Pausing",
            description="Playing player ▶️" if player.paused else "Pausing player ⏸️",
        )

        embed.color = discord.Color.blurple()
        await player.set_pause(not player.paused)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    @app_commands.guild_only()
    async def shuffle(self, interaction: discord.Interaction):
        await self.ensure_voice(interaction)
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        embed = discord.Embed(
            title="Un-Shuffling" if player.shuffle else "Shuffling",
            description="Un-Shuffling player"
            if player.shuffle
            else "Shuffling player ",
        )
        embed.color = discord.Color.blurple()

        player.set_shuffle(not player.shuffle)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remove", description="remove a track from the queue")
    @app_commands.describe(song="the track # for which to remove")
    @app_commands.guild_only()
    async def remove(
        self, interaction: discord.Interaction, song: app_commands.Range[int, 1]
    ):
        await self.ensure_voice(interaction)
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if not player.is_connected:
            return

        q: list = player.queue
        ephemeral = False
        try:
            q.pop(song - 1)
            embed = discord.Embed(
                title="Removed Track!",
                color=discord.Color.blurple(),
                description=f"Removed track #{song}",
            )
        except Exception as error:
            embed = discord.Embed(title="Error!", color=0xFF1100)
            ephemeral = True

            if isinstance(error, IndexError):
                embed.description = f"There is no track #{song}"

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @remove.autocomplete("song")  # type: ignore
    @app_commands.guild_only()
    async def remove_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]] | None:
        player: lavalink.DefaultPlayer | None = self.client.lavalink.player_manager.get(  # type: ignore
            interaction.guild.id  # type: ignore
        )  # get the player as always

        if player is None or player.queue == []:
            return []

        titles = [track.title for track in player.queue]

        if len(current) == 0:
            return [
                app_commands.Choice(name=trackName, value=trackPosition + 1)
                for trackPosition, trackName in enumerate(titles[:5])
            ]

        matches = process.extract(
            current, titles, scorer=fuzz.token_sort_ratio, limit=5
        )

        positions = {title: position for position, title in enumerate(titles)}

        return [
            app_commands.Choice(name=trackTitle, value=trackPosition + 1)
            for trackTitle, trackPosition in {
                match[0]: positions[match[0]] for match in matches
            }.items()
        ]

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandInvokeError):
            if isinstance(error.original, MusicError):
                return await interaction.response.send_message(str(error.original), ephemeral=True)
        raise error


async def setup(bot: commands.Bot) -> None:
    await asyncio.sleep(5)
    await bot.add_cog(Music(bot))
