#!/usr/bin/env python

import asyncio
import logging
import websockets
import json
import ytmusicapi
import datetime

logging.basicConfig()


def error_event(error: str, message: str):
    return json.dumps({"event": "error", "error": error, "message": message})


class Guild:
    def __init__(self, id: str):
        self.id = id
        self.users = {}
        self.media_state = {
            "url": "",
            "title": "",
            "artist": "",
            "album": "",
            "art": "",
            "current_time": 0,
            "length": 0,
            "playing": False,
            "queue_index": -1,
        }
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
        return json.dumps(
            {
                "event": "queue",
                "queue": self.queue,
                "index": self.media_state["queue_index"],
            }
        )

    async def notify_all(self, string: str):
        if self.users:
            await asyncio.wait(
                [asyncio.create_task(u.send(string)) for u in self.users]
            )

    async def register(self, websocket):
        self.users[websocket] = {"id": hash(websocket)}
        await self.notify_all(self.users_event())
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
        self.media_state["playing"] = playing
        await self.notify_all(self.media_state_event())

    async def action_seek(self, websocket, time: int):
        # TODO: implement
        assert type(time) == int


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
                await websocket.send(error_event("RequestError", e))
            except AssertionError as e:
                await websocket.send(error_event("RequestError", "Malformed request."))

    finally:
        await guild.unregister(websocket)
        if not guild.users:
            # if the guild is empty, destroy it
            guilds.pop(guild_id)


start_server = websockets.serve(counter, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
