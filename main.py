import uvicorn
import json
import asyncio
import threading
from contextlib import asynccontextmanager
from pypresence import Client, ActivityType
from fastapi import FastAPI, Request
from pydantic import BaseModel
import queue
import time
from datetime import datetime, timedelta

RPC = Client("1492702030958170272")
rpc_queue = queue.Queue()

global stored_song_data
stored_song_data = {}

def rpc_worker():
    RPC.start()

    while True:
        data = rpc_queue.get()
        if data is None:
            break
        
        if data['type'] == "BeatmapInitialized":
            current_time = int(time.time())

            stored_song_data = data
            stored_song_data['start_time'] = current_time
            stored_song_data['duration'] = int(data['duration'])

            total_paused_duration = 0
            pause_start_time = None

            end_time = current_time + stored_song_data['duration']

            dt_object = datetime.fromtimestamp(current_time)
            new_dt = dt_object + timedelta(seconds=int(data['duration']))
            new_epoch = new_dt.timestamp()
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                details=f"{data['author']} - {data['title']} | {', '.join(list(dict.fromkeys(data['mappers']))) or 'Unknown'}",
                state=f"Status: Playing | {data['difficulty']} | Solo",
                start=current_time,
                end=end_time,
                small_image="quest",
                small_text="Meta Quest"
            )
        
        if data['type'] == "LobbyPlayerOnConnect":
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                details="Status: Multiplayer Lobby",
                state=f"{data['playerCount']} players waiting...",
                small_image="quest",
                small_text="Meta Quest"
            )
        
        if data['type'] == "LobbyPlayerOnDisconnect":
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                details="Status: Multiplayer Lobby",
                state=f"{data['playerCount']} players waiting...",
                small_image="quest",
                small_text="Meta Quest"
            )
        
        if data['type'] == "MultiplayerBeatmapInitialized":
            current_time = int(time.time())
            end_time = current_time + data['duration']
            time.sleep(5)
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                details=f"{data['author']} - {data['title']} | {', '.join(list(dict.fromkeys(data['mappers']))) or 'Unknown'}",
                state=f"Status: Playing | {data['difficulty']} | Multiplayer",
                start=current_time,
                end=end_time,
                small_image="quest",
                small_text="Meta Quest"
            )
        
        if data['type'] == "MainMenuInitialized":
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                state="Status: Main Menu",
                small_image="quest",
                small_text="Meta Quest"
            )
        if data['type'] == "LevelSelectionMenuInitialized":
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                state="Status: Level Selection Menu",
                small_image="quest",
                small_text="Meta Quest"
            )
        
        if data['type'] == "BeatmapCleared":
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                details=f"{data['author']} - {data['title']} | {', '.join(list(dict.fromkeys(data['mappers']))) or 'Unknown'}",
                state=f"Status: Cleared | {data['difficulty']}",
                small_image="quest",
                small_text="Meta Quest"
            )
        
        if data['type'] == "BeatmapFailed":
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                details=f"{stored_song_data['author']} - {stored_song_data['title']} | {', '.join(list(dict.fromkeys(stored_song_data['mappers']))) or 'Unknown'}",
                state=f"Status: Failed | {stored_song_data['difficulty']}",
                small_image="quest",
                small_text="Meta Quest"
            )

        if data['type'] == "BeatmapPaused":
            pause_start_time = int(time.time())

            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                state="Level paused",
            )
        if data['type'] == "BeatmapResumed":
            current_time = int(time.time())
            
            if pause_start_time is not None:
                total_paused_duration += current_time - pause_start_time
                pause_start_time = None

            adjusted_start = stored_song_data['start_time'] + total_paused_duration
            adjusted_end = adjusted_start + stored_song_data['duration']

            dt_object = datetime.fromtimestamp(current_time)
            new_dt = dt_object + timedelta(seconds=int(stored_song_data['duration']))
            new_epoch = new_dt.timestamp()
            RPC.set_activity(
                activity_type=ActivityType.PLAYING,
                state=f"{stored_song_data['author']} - {stored_song_data['title']}",
                details=f"Mapped by {', '.join(stored_song_data['mappers']) or 'Unknown'} | {stored_song_data['difficulty']}",
                start=adjusted_start,
                end=adjusted_end
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=rpc_worker, daemon=True)
    thread.start()
    yield
    rpc_queue.put(None)
    RPC.close()


app = FastAPI(lifespan=lifespan)

@app.post("/sendData")
async def post_root(request: Request):
    body = await request.body()
    data = json.loads(body.decode("utf-8"))
    rpc_queue.put(data)
    print(data)
    return data


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
