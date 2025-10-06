from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
import calendar
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from models import db, User, Event
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/current-month")
@login_required
def current_month():
    now = datetime.now()
    return redirect(url_for('events_by_month', year=now.year, month=now.month))

@app.route("/month/<int:year>/<int:month>")
@login_required
def events_by_month(year, month):
    events = Event.query.filter_by(user_id=current_user.id).filter(
        db.extract('year', Event.date) == year,
        db.extract('month', Event.date) == month
    ).all()
    
    
    today = datetime.now().date()
    
    
    week_start = today
    week_end = today + timedelta(days=7)
    upcoming_week = Event.query.filter_by(user_id=current_user.id).filter(
        Event.date >= week_start,
        Event.date < week_end
    ).order_by(Event.date).all()
    
    
    next_week_start = week_end
    next_week_end = next_week_start + timedelta(days=7)
    upcoming_next_week = Event.query.filter_by(user_id=current_user.id).filter(
        Event.date >= next_week_start,
        Event.date < next_week_end
    ).order_by(Event.date).all()
    
    
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    
    all_month_events = Event.query.filter_by(user_id=current_user.id).filter(
        Event.date >= month_start,
        Event.date <= month_end
    ).order_by(Event.date).all()
    
    
    upcoming_month = []
    for event in all_month_events:
        
        if not (week_start <= event.date < week_end) and not (next_week_start <= event.date < next_week_end):
            upcoming_month.append(event)
    
    
    cal = calendar.Calendar(firstweekday=0)  
    month_days = cal.monthdayscalendar(year, month)
    
    month_names = ['', 'Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень',
                   'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень']
    month_name = month_names[month]
    
    
    days = []
    for week in month_days:
        for day_num in week:
            if day_num != 0:  
                day_date = date(year, month, day_num)
                day_events = [e for e in events if e.date == day_date]
                is_today = (day_date == today)
                is_current_month = True
                
                days.append({
                    'day': day_num,
                    'events': day_events,
                    'is_today': is_today,
                    'is_current_month': is_current_month,
                    'full_date': day_date.strftime('%Y-%m-%d')
                })
            else:
                days.append({
                    'day': '',
                    'events': [],
                    'is_today': False,
                    'is_current_month': False,
                    'full_date': ''
                })
    
    years = list(range(2020, 2031))
    
    return render_template("month.html", 
                         year=year, 
                         month=month,
                         month_name=month_name,
                         days=days,
                         years=years,
                         today=today,
                         upcoming_week=upcoming_week,
                         upcoming_next_week=upcoming_next_week,
                         upcoming_month=upcoming_month)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('current_month'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Вітаємо! Ви успішно увійшли в систему.', 'success')
            return redirect(url_for('current_month'))
        else:
            flash('Невірне ім\'я користувача або пароль.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('current_month'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Користувач з таким іменем вже існує', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Користувач з таким email вже існує', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Вітаємо! Ваш акаунт успішно створено.', 'success')
        return redirect(url_for('current_month'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви успішно вийшли з системи.', 'info')
    return redirect(url_for('home'))

@app.route("/day/<date>")
@login_required
def events_by_day(date):
    day_date = datetime.strptime(date, "%Y-%m-%d").date()
    events = Event.query.filter_by(user_id=current_user.id, date=day_date).order_by(Event.created_at).all()
    message = request.args.get("message")
    return render_template("dayfeed.html", date=day_date, events=events, message=message)

@app.route("/add/<date>")
@login_required
def add_event_form(date):
    event_date = datetime.strptime(date, "%Y-%m-%d").date()
    return render_template("add_event.html", date=event_date)

@app.route("/add", methods=["POST"])
@login_required
def add_event():
    title = request.form["title"]
    date_str = request.form["date"]
    desc = request.form.get("description", "")
    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    event = Event(
        title=title,
        date=event_date,
        description=desc,
        user_id=current_user.id
    )
    
    db.session.add(event)
    db.session.commit()
    
    flash('Подію успішно додано!', 'success')
    
    if request.referrer and "/add/" in request.referrer:
        return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d")))
    return redirect(url_for("events_by_month", year=event_date.year, month=event_date.month))

@app.route("/edit/<int:event_id>")
@login_required
def edit_event_form(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    return render_template("edit_event.html", event=event)

@app.route("/edit/<int:event_id>", methods=["POST"])
@login_required
def edit_event(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    
    if event:
        event.title = request.form["title"]
        event.description = request.form["description"]
        event.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        db.session.commit()
        flash('Подію успішно оновлено!', 'success')
    
    return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d")))

@app.route("/delete/<int:event_id>")
@login_required
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    
    if event:
        event_date = event.date
        db.session.delete(event)
        db.session.commit()
        flash('Подію успішно видалено!', 'success')
        return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d")))
    
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)