# youtube-sync
A server application to synchronise YouTube streams via websockets designed for YouTube Music.

A sample instance is running at wss://api.eggworld.tk/music.

## Prerequisites

```
ytmusicapi
websockets
```

## Clients

To open a connection, clients require a `guild` argument (basically a group ID) in the URL and will be assigned to that guild, able to send and receive updates to/from only that guild.

Sample connection:
```js
const ws = new WebSocket("wss://api.eggworld.tk/music?guild=1234567890")
```

The server will emit three possible state changes in JSON, defined by the `type` field:

### User change event

This event is emitted to the current guild when a user profile is updated or the number of online users changes. It sends a full list of users that are attending the current stream.

Sample event:

```json
{
    "type": "user",
    "count": 1,
    "users": [
        {
            "name": "Bobby",
            "identifier": "",
            "art": "https://cdn.discordapp.com/12345678.png"
        }
    ]
}
```

### Media change event

This event is emitted to the current guild on initial join or when a seek or jump request is submitted. It sends details regarding the currently playing video. A link to the stream is provided via an embed link, and the time sent is the seconds elapsed since the start of the video. It is guaranteed to be smaller than the length of the video.

Sample event:

```json
{
    "type": "media",
    "url": "https://youtube.com/embed/xxxxxxx",
    "current_time": 100,
    "length": 250,
    "playing": true,
    "title": "Baby Shark",
    "artist": "Pinkfong",
    "album": "Baby Shark",
    "art": "https://i.ytimg.com/xxxxxx"
}
```

### Queue change event

This event is emitted to the current guild on initial join or when the current queue changes, including when entries are added/removed to/from the queue or the current index changes.

```json
{
    "type": "queue",
    "queue": [
        {
            "url": "https://youtube.com/embed/xxxxxxx",
            "length": 100,
            "title": "Baby Shark",
            "artist": "Pinkfong",
            "album": "Baby Shark",
            "art": "https://i.ytimg.com/xxxxxx"
        }
    ]
}
```