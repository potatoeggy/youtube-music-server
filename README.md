# youtube-sync
A server application to synchronise YouTube streams via websockets designed for YouTube Music.

To open a connection, clients require a `guild` argument (basically a group ID) in the URL and will be assigned to that guild, allowing them to send and receive updates to/from only that guild.

Sample connection:
```js
const ws = new WebSocket("wss://api.eggworld.tk/music?guild=1234567890")
```

## Prerequisites

```
ytmusicapi
websockets
```

## Receiving events

The server will emit four possible state changes in JSON, defined by the `event` field:

### User change

This event is emitted to the current guild when a user profile is updated or the number of online users changes. It sends a full list of users that are attending the current stream.

Sample event:

```json
{
    "event": "user",
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

### Media change

This event is emitted to the current guild on initial join or when a seek or jump request is submitted. It sends details regarding the currently playing video. A link to the stream is provided via an embed link, and the time sent is the seconds elapsed since the start of the video. It is guaranteed to be smaller than the length of the video.

Sample event:

```json
{
    "event": "media",
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

### Queue change

This event is emitted to the current guild on initial join or when the current queue changes, including when entries are added/removed to/from the queue or the current index changes.

```json
{
    "event": "queue",
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

### Error

This event is emitted generally only when a request is sent that has failed in some way. It contains an error string and a more detailed message.

Sample error:

```json
{
    "event": "error",
    "error": "GuildError",
    "message": "Guild not specified in path."
}
```

Sample error:
```json
{
    "event": "error",
    "error": "RequestError",
    "message": "Malformed request."
}
```

## Sending actions

There are seven currently defined actions for clients to send to the server via the websocket in JSON, defined by the `action` field.

### Set the user profile

This information is used to share with other users and is not mandatory. It accepts a display name, an identifier (currently unused), and/or a URL to an image on the internet. Each field is optional.

Sample request:

```json
{
    "action": "set_profile",
    "name": "Eggy", // optional, not including it will reset any existing name
    "identifier": "Eggy#1234", // optional, not including it will reset any existing  identifier
    "art": "https://cdn.discordapp.com/xxxxxx.png" // optional, not including it will reset any existing art
}
```

### Pause/resume playback

This is used to globally pause/play video for all users. If the video is in the same state as the request sent (e.g., already playing and a play request is sent), an error response will be returned.

Sample request:

```json
{
    "action": "play"
}
```

Sample request:

```json
{
    "action": "pause"
}
```

**Error response: `NoChangeError`**

```json
{
    "event": "error",
    "error": "NoChangeError",
    "message": "The video is already playing/paused."
}
```

### Seek to a time in the current video

This action is used to tell all other players to seek to a certain timestamp in the video, represented in the number of seconds since the beginning of the video. It cannot exceed the length of the video.

Sample request:

```json
{
    "action": "seek",
    "time": 100
}
```

**Error response: `TimeLimitExceededError`**

```json
{
    "event": "error",
    "error": "TimeLimitExceededError",
    "message": "The seek time specified is greater than the length of the video."
}
```

### Add a video to the queue

This action adds a video to the queue either via search query or embed/non-embed URL. If a URL is provided, it will take priority over a query.

Sample request:

```json
{
    "action": "add_media",
    "url": "https://youtube.com/watch?xxxxxx",
    "query": "baby shark"
}
```

**Error response: `InvalidVideoError`**

```json
{
    "event": "error",
    "error": "InvalidVideoError",
    "message": "The video URL provided was not a valid video."
}
```

### Remove a video from the queue

This action removes a video via an index in the queue, where `0` is the currently playing video.

Sample request:

```json
{
    "action": "remove_media",
    "index": 1
}
```

**Error response: `IndexError`**

```json
{
    "event": "error",
    "error": "IndexError",
    "message": "The index provided is out of bounds."
}
```

### Jump to a video in the queue

This action changes the currently playing video to a different video in the queue at a certain index, where `0` is the currently playing video.

Sample request:

```json
{
    "action": "jump",
    "index": 1,
    "time": 100, // optional, defaults to 0
}
```

**Error response: `IndexError`**

```json
{
    "event": "error",
    "error": "IndexError",
    "message": "The index provided is out of bounds."
}
```

**Error response: `TimeLimitExceededError`**

```json
{
    "event": "error",
    "error": "TimeLimitExceededError",
    "message": "The seek time specified is greater than the length of the video."
}
```

### Mark the current video as finished

This event notifies the server that the current video has finished playing. Currently, only when all users have submitted a `finished` request will the next item in the queue play automatically.

```json
{
    "action": "finished"
}