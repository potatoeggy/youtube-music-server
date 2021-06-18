#!/usr/bin/env python

import asyncio
import logging
import websockets
import json
import ytmusicapi

logging.basicConfig()


class Guild:
    __slots__ = ["media_state", "users", "queue", "id"]

    def __init__(self, id: str):
        self.id = id
        self.users = {}
        self.media_state = {
            "url": "",
            "title": "",
            "artist": "",
            "album": "",
            "art": "",
            "queue_index": -1,
        }
        self.queue = []
        # TODO: there are a couple of options to determine if a song ends
        # 1. we can not process it ourselves, relying on clients to push
        # a `finished` request which seems easiest - disregarding majority
        # 2. we can time it ourselves and force all clients to push

        # if we require clients, we can require a majority to say push
        # or we can push when only one finishes
        # or we can push only when all finish
        # issue with the last one is that buffering can ruin the experience

    def media_state_event(self):
        return json.dumps({"type": "state", **self.media_state})

    def users_event(self):
        return json.dumps(
            {"type": "users", "count": len(self.users), "users": self.users.values()}
        )

    def queue_event(self):
        return json.dumps(
            {
                "type": "queue",
                "queue": self.queue,
                "index": self.media_state["queue_index"],
            }
        )

    async def notify_media_state(self):
        # TODO: reorg functions so that there is much less redundancy
        if self.users:
            await asyncio.wait(
                [
                    asyncio.create_task(u.send(self.media_state_event()))
                    for u in self.users
                ]
            )

    async def notify_users(self):
        if self.users:
            await asyncio.wait(
                [asyncio.create_task(u.send(self.users_event())) for u in self.users]
            )

    async def notify_queue(self):
        if self.users:
            await asyncio.wait(
                [asyncio.create_task(u.send(self.queue_event())) for u in self.users]
            )

    async def register(self, websocket):
        self.users[websocket] = {}
        await self.notify_users()
        await websocket.send(self.media_state_event())

    async def unregister(self, websocket):
        self.users.pop(websocket, None)
        await self.notify_users()


guilds = {}


async def counter(websocket, path: str):
    # TODO: consider copying Genshin's API system
    guild_index: int = path.find("?guild=") + 7
    if guild_index == 6:
        # if the string was not found (-1)
        await websocket.send(
            {
                "type": "error",
                "error": "GuildError",
                "message": "Guild not specified in path.",
            }
        )
        return

    guild_id: str = path[guild_index:]

    if not guild_id in guilds:
        guilds[guild_id] = Guild(guild_id)
    guild: Guild = guilds[guild_id]

    try:
        await guild.register(websocket)
        async for message in websocket:
            data = json.loads(message)
            try:
                if True:
                    pass
                else:
                    logging.error(f"unsupported event: {data}")
            except KeyError:
                logging.error(f"unsupported event: {data}")
    finally:
        await guild.unregister(websocket)


start_server = websockets.serve(counter, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
