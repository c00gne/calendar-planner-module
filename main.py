from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
import calendar
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from models import db, User, Event, Contract
from config import Config
from analytics import Analytics

Analytics.log("Flask app started")

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
            Analytics.log(f"User logged in: {user.username}")
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
        Analytics.log(f"New user registered: {username}")
        flash('Вітаємо! Ваш акаунт успішно створено.', 'success')
        return redirect(url_for('current_month'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    Analytics.log(f"User logged out: {current_user.username}")
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
    Analytics.log(f"User {current_user.username} added event: {title} on {event_date}")

    
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
        Analytics.log(f"User {current_user.username} edited event #{event.id}")
        flash('Подію успішно оновлено!', 'success')
    return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d")))

@app.route("/delete/<int:event_id>")
@login_required
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    
    if event:
        event_date = event.date
        Analytics.log(f"User {current_user.username} deleted event #{event.id}")
        db.session.delete(event)
        db.session.commit()
        flash('Подію успішно видалено!', 'success')
        return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d")))
    
    return redirect(url_for("home"))

# === ДОПОМІЖНА ФУНКЦІЯ ДЛЯ РОЗРАХУНКУ ДАТ ===
def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

# === ЛОГІКА СТВОРЕННЯ ДОГОВОРУ (ТИЖДЕНЬ 2) ===
@app.route("/add_contract", methods=["GET", "POST"])
@login_required
def add_contract():
    if request.method == "POST":
        # 1. Отримуємо дані з форми
        number = request.form["number"]
        client = request.form["client"]
        amount = float(request.form["amount"])
        start_date_str = request.form["start_date"]
        duration = int(request.form["duration"])
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        # 2. Створюємо сам договір в базі
        contract = Contract(
            number=number,
            client_name=client,
            amount=amount,
            start_date=start_date,
            duration_months=duration,
            user_id=current_user.id
        )
        db.session.add(contract)
        db.session.flush() # Це важливо! Щоб отримати contract.id до commit

        # 3. МАГІЯ: Генерація графіку платежів
        monthly_payment = amount / duration # Простий розрахунок платежу
        
        for i in range(duration):
            # Розрахунок дати наступного платежу
            payment_date = add_months(start_date, i)
            
            # Створення події-платежу
            event = Event(
                title=f"Платіж: {client} ({i+1}/{duration})",
                description=f"Сума: {monthly_payment:.2f} грн. Договір №{number}. Внесок {i+1} з {duration}",
                date=payment_date,
                user_id=current_user.id,
                priority='high',      # Автоматично ставимо високий пріоритет
                event_type='payment', # Позначаємо як платіж
                contract_id=contract.id
            )
            db.session.add(event)

        db.session.commit()
        Analytics.log(f"User {current_user.username} created contract {number} with {duration} auto-events")
        
        flash(f'Договір створено! Графік платежів на {duration} міс. згенеровано.', 'success')
        return redirect(url_for('current_month'))

    return render_template("add_contract.html")

# === АНУЛЮВАННЯ ДОГОВОРУ ===
@app.route("/cancel_contract", methods=["GET", "POST"])
@login_required
def cancel_contract():
    if request.method == "POST":
        query = request.form["query"].strip() # Отримуємо текст
        
        # Шукаємо договір за номером АБО назвою клієнта
        contract = Contract.query.filter(
            (Contract.user_id == current_user.id) & 
            ((Contract.number == query) | (Contract.client_name == query))
        ).first()

        if contract:
            deleted_info = f"{contract.number} ({contract.client_name})"
            
            # Видаляємо договір -> база сама видалить всі події (Cascade)
            db.session.delete(contract)
            db.session.commit()
            
            Analytics.log(f"User {current_user.username} cancelled contract: {deleted_info}")
            flash(f'Договір {deleted_info} успішно розірвано. Всі події видалено.', 'warning')
            return redirect(url_for('current_month'))
        else:
            flash(f'Договір за запитом "{query}" не знайдено. Перевірте назву.', 'danger')

    return render_template("cancel_contract.html")

if __name__ == "__main__":
    with app.app_context():
         db.create_all()
    
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        Analytics.log("Flask app shutdown (KeyboardInterrupt)")
    finally:
        Analytics.log("Flask app shutdown")








    