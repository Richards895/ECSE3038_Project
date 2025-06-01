from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv 
import motor.motor_asyncio
from datetime import datetime, timedelta
import requests
import re
import os


load_dotenv()
app = FastAPI()

origins = [
    "https://simple-smart-hub-client.netlify.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connection = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
SimpleSmartHub_db = connection.SimpleSmartHub
settings_collection = SimpleSmartHub_db.settings
logs_collection = SimpleSmartHub_db.sensor_logs

regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_time(time_str: str) -> timedelta:
    parts = regex.match(time_str)
    if not parts:
        raise ValueError("Invalid duration format")
    parts = parts.groupdict()
    time_params = {name: int(param) for name, param in parts.items() if param}
    return timedelta(**time_params)

class UserSettings(BaseModel):
    user_temp: float
    user_light: str
    light_duration: str

@app.put("/settings")
async def set_user_settings(settings: UserSettings):
    user_light_time = settings.user_light

    if user_light_time.lower() == "sunset":
        lat, lon = 18.1096, -77.2975
        res = requests.get(f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&formatted=0")
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch sunset time")
        user_light_time = res.json()["results"]["sunset"]
        user_light_time = datetime.fromisoformat(user_light_time).astimezone().time().strftime("%H:%M:%S")

    light_on_dt = datetime.strptime(user_light_time, "%H:%M:%S")

    try:
        duration_td = parse_time(settings.light_duration)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid duration format: {e}")

    light_off_dt = (datetime.combine(datetime.today(), light_on_dt.time()) + duration_td).time()

    settings_doc = {
        "user_temp": settings.user_temp,
        "user_light": light_on_dt.strftime("%H:%M:%S"),
        "light_time_off": light_off_dt.strftime("%H:%M:%S"),
    }
    await settings_collection.delete_many({})
    result = await settings_collection.insert_one(settings_doc)
    settings_doc["_id"] = str(result.inserted_id)

    return settings_doc

@app.get("/control")
async def device_control(
    temp: float,
    motion: int,
    current_time: str
):
    timestamp = datetime.now().isoformat()
    await logs_collection.insert_one({
        "temperature": temp,
        "motion": motion,
        "timestamp": timestamp,
    })

    settings = await settings_collection.find_one()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    fan_on = False
    light_on = False

    try:
        now = datetime.strptime(current_time, "%H:%M:%S").time()
        light_on_time = datetime.strptime(settings["user_light"], "%H:%M:%S").time()
        light_off_time = datetime.strptime(settings["light_time_off"], "%H:%M:%S").time()

        if motion and temp > settings["user_temp"]:
            fan_on = True
        if motion and light_on_time <= now <= light_off_time:
            light_on = True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")

    return {"fan": fan_on, "light": light_on}

@app.get("/graph")
async def graph_data(size: Optional[int] = 10):
    cursor = logs_collection.find().sort("timestamp", -1).limit(size)
    entries = await cursor.to_list(length=size)
    entries.reverse()  

    return [
        {
            "temperature": entry["temperature"],
            "presence": bool(entry["motion"]),
            "datetime": entry["timestamp"],
        }
        for entry in entries
    ]
