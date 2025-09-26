from datetime import date

class Event:
    def __init__(self, title: str, event_date: date, description: str = ""):
        self.title = title
        self.date = event_date
        self.description = description

    def __repr__(self):
        return f"{self.date}: {self.title} - {self.description}"


class EventManager:
    def __init__(self):
        self.events = []

    def add_event(self, event: Event):
        self.events.append(event)

    def get_events_by_day(self, day: date):
        return [e for e in self.events if e.date == day]

    def get_events_by_month(self, year: int, month: int):
        return [e for e in self.events if e.date.year == year and e.date.month == month]
