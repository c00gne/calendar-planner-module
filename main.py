from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, date
import calendar
from events import Event, EventManager

app = Flask(__name__)
manager = EventManager()

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/day/<date>")
def events_by_day(date):
    day_date = datetime.strptime(date, "%Y-%m-%d").date()
    events = manager.get_events_by_day(day_date)
    message = request.args.get("message")
    return render_template("dayfeed.html", date=day_date, events=events, message=message)

@app.route("/add/<date>")
def add_event_form(date):
    event_date = datetime.strptime(date, "%Y-%m-%d").date()
    return render_template("add_event.html", date=event_date)

@app.route("/add", methods=["POST"])
def add_event():
    title = request.form["title"]
    date_str = request.form["date"]
    desc = request.form.get("description", "")
    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    manager.add_event(Event(title, event_date, desc))
    # Якщо додавання з форми дня — показати фідбек
    if request.referrer and "/add/" in request.referrer:
        return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d"), message="Подію додано!"))
    # Інакше повертаємо на місяць
    return redirect(url_for("events_by_month", year=event_date.year, month=event_date.month))

@app.route("/month/<int:year>/<int:month>")
def events_by_month(year, month):
    events = manager.get_events_by_month(year, month)
    num_days = calendar.monthrange(year, month)[1]
    days = []
    for d in range(1, num_days + 1):
        day_date = date(year, month, d)
        day_events = [e for e in events if e.date == day_date]
        days.append({"day": d, "events": day_events})
    return render_template("month.html", year=year, month=month, days=days)


@app.route("/edit/<int:event_id>")
def edit_event_form(event_id):
    event = manager.get_event_by_id(event_id)
    return render_template("edit_event.html", event=event)

@app.route("/edit/<int:event_id>", methods=["POST"])
def edit_event(event_id):
    event = manager.get_event_by_id(event_id)
    if event:
        event.title = request.form["title"]
        event.description = request.form["description"]
        event.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
    return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d"), message="Подію оновлено!"))

@app.route("/delete/<int:event_id>")
def delete_event(event_id):
    event = manager.get_event_by_id(event_id)
    if event:
        manager.delete_event(event_id)
        return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d"), message="Подію видалено!"))
    return redirect(url_for("home"))



if __name__ == "__main__":
    app.run(debug=True)