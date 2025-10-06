import json
import os
from datetime import date

class Event:
    _id_counter = 1

    def __init__(self, title: str, event_date: date, description: str = ""):
        self.id = Event._id_counter
        Event._id_counter += 1
        self.title = title
        self.date = event_date
        self.description = description

    def __repr__(self):
        return f"{self.date}: {self.title} - {self.description}"


class EventManager:
    def __init__(self):
        self.events = []
        self.load_from_file()  # автоматично підвантажує події при старті

    def add_event(self, event: Event):
        self.events.append(event)
        self.save_to_file()

    def get_events_by_day(self, day: date):
        return [e for e in self.events if e.date == day]

    def get_events_by_month(self, year: int, month: int):
        return [e for e in self.events if e.date.year == year and e.date.month == month]

    def get_event_by_id(self, event_id: int):
        for e in self.events:
            if e.id == event_id:
                return e
        return None

    def delete_event(self, event_id: int):
        self.events = [e for e in self.events if e.id != event_id]
        self.save_to_file()

    def edit_event(self, event_id: int, new_title: str, new_description: str):
        event = self.get_event_by_id(event_id)
        if event:
            event.title = new_title
            event.description = new_description
            self.save_to_file()

    def save_to_file(self, filename="events.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                [ {"id": e.id, "title": e.title, "date": e.date.isoformat(), "description": e.description}
                  for e in self.events ],
                f, ensure_ascii=False, indent=4
            )

    def load_from_file(self, filename="events.json"):
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for d in data:
                    ev = Event(d["title"], date.fromisoformat(d["date"]), d.get("description", ""))
                    ev.id = d["id"]
                    self.events.append(ev)
                # поновлюємо лічильник ID
                if self.events:
                    Event._id_counter = max(e.id for e in self.events) + 1
