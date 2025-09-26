from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from events import Event, EventManager

app = Flask(__name__)
manager = EventManager()

@app.route("/")
def index():
    return render_template("index.html", events=manager.events)

@app.route("/add", methods=["POST"])
def add_event():
    title = request.form["title"]
    date_str = request.form["date"]
    desc = request.form.get("description", "")
    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    manager.add_event(Event(title, event_date, desc))
    return redirect(url_for("index"))

@app.route("/day/<day>")
def events_by_day(day):
    day_date = datetime.strptime(day, "%Y-%m-%d").date()
    events = manager.get_events_by_day(day_date)
    return render_template("index.html", events=events)

@app.route("/month/<int:year>/<int:month>")
def events_by_month(year, month):
    events = manager.get_events_by_month(year, month)
    return render_template("index.html", events=events)

if __name__ == "__main__":
    app.run(debug=True)
