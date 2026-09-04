from abc import ABC, abstractmethod
from typing import Dict, Any, List
import random
import numpy as np
from datetime import datetime, timedelta
import os
import requests

class LiveTrainDataProvider(ABC):
    @abstractmethod
    def get_all_active_trains(self) -> List[str]:
        pass

    @abstractmethod
    def get_train_status(self, train_no: str) -> Dict[str, Any]:
        pass

class MockLiveDataProvider(LiveTrainDataProvider):
    def __init__(self, routes, train_info, num_trains=6):
        self.routes = routes
        self.train_info = train_info
        self.active_trains = {}
        self._init_trains(num_trains)

    def _init_trains(self, num_trains):
        all_trains = list(self.train_info.keys())
        selected = random.sample(all_trains, min(num_trains, len(all_trains)))
        for train_no in selected:
            route_id = self.train_info[train_no]
            route = self.routes[route_id]
            idx = random.randint(0, len(route)-2)
            delay = random.uniform(0, 15)
            weather = random.choices(["clear", "rain", "fog"], weights=[0.7,0.2,0.1])[0]
            dist = route[idx+1]["distance"] - route[idx]["distance"]
            scheduled_time = (dist / 60) * 60
            avg_speed = random.uniform(40, 80)
            hour = random.choice([7,8,9,17,18,19]) if random.random()<0.6 else random.randint(6,22)
            self.active_trains[train_no] = {
                "train_no": train_no,
                "route_id": route_id,
                "station_index": idx,
                "current_station": route[idx]["station"],
                "next_station": route[idx+1]["station"],
                "distance_to_next": dist,
                "scheduled_time_to_next": scheduled_time,
                "current_delay": delay,
                "avg_speed_last_segment": avg_speed,
                "hour_of_day": hour,
                "day_of_week": datetime.now().weekday(),
                "weather": weather,
                "trains_ahead": random.randint(0, 3),
                "historical_avg_delay": random.uniform(2, 10),
                "last_update": datetime.now()
            }

    def get_all_active_trains(self):
        return list(self.active_trains.keys())

    def get_train_status(self, train_no):
        if train_no in self.active_trains:
            train = self.active_trains[train_no]
            # Simulate slight updates
            train["hour_of_day"] = datetime.now().hour
            train["day_of_week"] = datetime.now().weekday()
            train["current_delay"] += random.uniform(-1, 2)
            train["current_delay"] = max(0, train["current_delay"])
            train["avg_speed_last_segment"] += random.uniform(-5, 5)
            train["avg_speed_last_segment"] = max(30, train["avg_speed_last_segment"])
            if random.random() < 0.1:  # move to next station occasionally
                route = self.routes[train["route_id"]]
                idx = train["station_index"]
                if idx < len(route)-2:
                    train["station_index"] = idx + 1
                    train["current_station"] = route[idx+1]["station"]
                    train["next_station"] = route[idx+2]["station"]
                    dist = route[idx+2]["distance"] - route[idx+1]["distance"]
                    train["distance_to_next"] = dist
                    train["scheduled_time_to_next"] = (dist / 60) * 60
                    train["current_delay"] = max(0, train["current_delay"] - random.uniform(0,5))
                    train["avg_speed_last_segment"] = random.uniform(40, 80)
            return train.copy()
        return None

class RealAPIDataProvider(LiveTrainDataProvider):
    def __init__(self):
        self.api_key = os.getenv("INDIANRAIL_API_KEY")
        if not self.api_key:
            raise ValueError("INDIANRAIL_API_KEY environment variable not set")
        self.base_url = "https://indianrailapi.com/api/v2"

    def get_all_active_trains(self):
        # Placeholder – implement based on API
        return ["12345", "67890"]

    def get_train_status(self, train_no):
        url = f"{self.base_url}/livetrainstatus/apikey/{self.api_key}/trainnumber/{train_no}/"
        response = requests.get(url)
        data = response.json()
        # Parse as per API response
        return {
            "train_no": train_no,
            "route_id": "R1",
            "station_index": 0,
            "current_station": data.get("current_station", ""),
            "next_station": data.get("next_station", ""),
            "distance_to_next": data.get("distance_to_next", 0),
            "scheduled_time_to_next": data.get("scheduled_time_to_next", 0),
            "current_delay": data.get("delay", 0),
            "avg_speed_last_segment": data.get("speed", 0),
            "hour_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "weather": data.get("weather", "clear"),
            "trains_ahead": 0,
            "historical_avg_delay": 5
        }