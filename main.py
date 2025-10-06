from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, date
import calendar
from events import Event, EventManager
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from models import db, User
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

manager = EventManager()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/")
def home():
    """Главная страница с приветствием"""
    return render_template("home.html")

@app.route("/current-month")
@login_required
def current_month():
    """Перенаправляет на текущий месяц"""
    now = datetime.now()
    return redirect(url_for('events_by_month', year=now.year, month=now.month))

@app.route("/month/<int:year>/<int:month>")
@login_required
def events_by_month(year, month):
    events = manager.get_events_by_month(year, month)
    
    # Создаем календарь на месяц
    cal = calendar.Calendar(firstweekday=0)  # Понедельник первый день
    month_days = cal.monthdayscalendar(year, month)
    
    # Название месяца
    month_names = ['', 'Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень',
                   'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень']
    month_name = month_names[month]
    
    # Текущая дата
    today = datetime.now().date()
    
    # Формируем дни для отображения
    days = []
    for week in month_days:
        for day_num in week:
            if day_num != 0:  # Игнорируем пустые дни (другие месяцы)
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
                # Добавляем пустые дни для выравнивания
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
                         today=today)

# Аутентификация
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('current_month'))  # Перенаправляем на текущий месяц
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('current_month'))  # После входа - на текущий месяц
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if current_user.is_authenticated:
        return redirect(url_for('current_month'))  # Если уже авторизован - на текущий месяц
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Користувач з таким іменем вже існує')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('current_month'))  # После регистрации - на текущий месяц
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

# Маршруты для событий
@app.route("/day/<date>")
@login_required
def events_by_day(date):
    day_date = datetime.strptime(date, "%Y-%m-%d").date()
    events = manager.get_events_by_day(day_date)
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
    manager.add_event(Event(title, event_date, desc))
    
    if request.referrer and "/add/" in request.referrer:
        return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d"), message="Подію додано!"))
    return redirect(url_for("events_by_month", year=event_date.year, month=event_date.month))

@app.route("/edit/<int:event_id>")
@login_required
def edit_event_form(event_id):
    event = manager.get_event_by_id(event_id)
    return render_template("edit_event.html", event=event)

@app.route("/edit/<int:event_id>", methods=["POST"])
@login_required
def edit_event(event_id):
    event = manager.get_event_by_id(event_id)
    if event:
        event.title = request.form["title"]
        event.description = request.form["description"]
        event.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
    return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d"), message="Подію оновлено!"))

@app.route("/delete/<int:event_id>")
@login_required
def delete_event(event_id):
    event = manager.get_event_by_id(event_id)
    if event:
        manager.delete_event(event_id)
        return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d"), message="Подію видалено!"))
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)