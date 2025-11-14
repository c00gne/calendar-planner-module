import datetime

class Analytics:
    LOG_FILE = "analytics.log"

    @staticmethod
    def log(event: str):
        with open(Analytics.LOG_FILE, "a", encoding="utf-8") as f:
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{time} — {event}\n")
