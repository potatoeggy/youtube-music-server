#!/usr/bin/env python

import asyncio
import logging
import websockets
import json
import ytmusicapi
import datetime

logging.basicConfig()
ytmusic = ytmusicapi.YTMusic()


def error_event(error: str, message: str):
    return json.dumps({"event": "error", "error": error, "message": message})


class Guild:
    def __init__(self, id: str):
        self.id = id
        self.users = {}
        self.media_state = {
            "current_time": 0,
            "length": 0,
            "playing": False,
            "queue_index": -1,
        }
        self.finished = 0
        self.last_update_time = datetime.datetime.now()
        self.queue = []

    def media_state_event(self, current_time: str = None) -> str:
        # TODO: if current_time is not none then set the time to current_time
        # otherwise calculate current_time (max of len and now + last push) and push
        return json.dumps({"event": "state", **self.media_state})

    def users_event(self) -> str:
        return json.dumps(
            {"event": "users", "count": len(self.users), "users": self.users.values()}
        )

    def queue_event(self) -> str:
        return json.dumps({"event": "queue", "queue": self.queue})

    async def notify_all(self, msg: str):
        if self.users:
            await asyncio.wait([asyncio.create_task(u.send(msg)) for u in self.users])

    async def register(self, websocket):
        self.users[websocket] = {"id": hash(websocket)}
        await self.notify_all(self.users_event())
        await websocket.send(self.queue_event())
        await websocket.send(self.media_state_event())

    async def unregister(self, websocket):
        self.users.pop(websocket, None)
        await self.notify_all(self.users_event())

    async def action_set_profile(self, websocket, data: dict):
        for key in ["name", "identifier", "art"]:
            assert type(key) == str
            if key in data:
                self.users[websocket][key] = data[key]
            else:
                self.users[websocket].pop(key, None)
        await self.notify_all(self.users_event())

    async def action_play_pause(self, websocket, playing: bool):
        assert type(playing) == bool
        # TODO: handle paused time when calculating current_time for new users
        self.media_state["playing"] = playing
        await self.notify_all(self.media_state_event())

    async def action_add(self, websocket, data: dict):
        assert "query" in data or "video_id" in data
        if "url" in data:
            try:
                song = ytmusic.get_song(data["video_id"])["videoDetails"]
            except KeyError:
                return await websocket.send(
                    error_event(
                        "InvalidVideoError",
                        "The video ID provided was not a valid video.",
                    )
                )

            song_metadata = {
                "url": f"https://youtube.com/embed/{song['videoId']}",
                "title": song["title"],
                "artist": song["author"],
                "length": int(song["lengthSeconds"]),
                "art": song["thumbnails"][0]["url"],
            }
        else:
            song = ytmusic.search(data["query"], "songs")[0]
            # TODO: consider using "video" over "song" for greater
            # but lower quality results as fallbacks

            song_metadata = {
                "url": f"https://youtube.com/embed/{song['videoId']}",
                "title": song["title"],
                "artist": ", ".join(a["name"] for a in song["artists"]),
                "length": sum(
                    i * int(p)
                    for i, p in zip(
                        [1, 60, 3600], reversed(song["duration"].split(":"))
                    )
                ),
                "art": song["thumbnails"][0]["url"],
            }
        play_immediately = self.media_state["queue_index"] == len(self.queue) - 1
        self.queue.append(song_metadata)
        await self.notify_all(self.queue_event())
        if play_immediately:
            self.action_jump(websocket, {"index": 1})

    async def action_remove(self, websocket, index: int):
        assert type(index) == int
        assert not index == 0
        try:
            del self.queue[index]
        except IndexError:
            return await websocket.send(
                error_event("IndexError", "The index provided is out of bounds.")
            )
        await self.notify_all(self.queue_event())

    async def action_jump(self, websocket, data: dict):
        assert type(data["index"]) == int
        time: int = 0
        if "time" in data:
            assert type(data["time"]) == int
            time = data["time"]
        if not 0 <= self.media_state["queue_index"] + data["index"] < len(self.queue):
            return await websocket.send(
                error_event(
                    "IndexError", "The index provided is out of bounds of the queue."
                )
            )

        video_index = self.media_state["queue_index"] + data["index"]
        if not 0 <= time <= self.queue[video_index]["length"]:
            return await websocket.send(
                error_event(
                    "TimeLimitExceededError",
                    "The seek time specified is greater than the length of the video.",
                )
            )

        self.finished = 0
        self.media_state = {
            "current_time": time,
            "length": self.queue[video_index]["length"],
            "playing": True,
            "queue_index": video_index,
        }
        await self.notify_all(self.media_state_event())

    async def action_mark_finished(self, websocket):
        self.finished += 1
        # TODO: this is unreliable in case a user marks as finished and leaves
        # before others finish
        # also if a user spams a finished action
        if self.finished == len(self.users):
            self.finished = 0
            if not self.media_state["queue_index"] == len(self.queue) - 1:
                # if there are more items in the queue
                self.action_jump(None, {"index": 1})
            # otherwise do nothing


guilds = {}


async def counter(websocket, path: str):
    # TODO: consider copying Hoyolab's API body format
    guild_index: int = path.find("?guild=") + len("?guild=")
    if guild_index < len("?guild="):
        # if index not found
        await websocket.send(error_event("GuildError", "Guild not specified in path."))
        return

    # get guild string from url
    guild_id: str = path[guild_index:]

    if not guild_id in guilds:
        # make a new guild if the current one does not exist
        guilds[guild_id] = Guild(guild_id)
    guild: Guild = guilds[guild_id]

    try:
        await guild.register(websocket)
        async for message in websocket:
            data = json.loads(message)
            try:
                action = data["action"]
            except KeyError:
                await websocket.send(error_event("RequestError", "No action given."))
                continue

            try:
                if action == "set_profile":
                    guild.action_set_profile(websocket, data)
                else:
                    await websocket.send(
                        error_event("RequestError", "Invalid action given.")
                    )
            except KeyError as e:
                await websocket.send(error_event("RequestError", "Malformed request."))
            except AssertionError as e:
                await websocket.send(error_event("RequestError", "Malformed request."))
            except Exception as e:
                await websocket.send(
                    error_event("Error", "An unexpected error occurred.")
                )
                logging.error(e)

    finally:
        await guild.unregister(websocket)
        if not guild.users:
            # if the guild is empty, destroy it
            guilds.pop(guild_id)


start_server = websockets.serve(counter, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
