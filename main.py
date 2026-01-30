from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
import calendar
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_mail import Mail, Message  # <--- [1] ІМПОРТ ПОШТИ
from models import db, User, Event, Contract
from config import Config
from analytics import Analytics

Analytics.log("Flask app started")

app = Flask(__name__)
app.config.from_object(Config)

# === ІНІЦІАЛІЗАЦІЯ ===
db.init_app(app)
mail = Mail(app)  # <--- [2] ЗАПУСК ПОШТИ

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# === ДОПОМІЖНА ФУНКЦІЯ ДЛЯ ДАТ ===
def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

@app.route("/")
def home():
    # Якщо користувач не увійшов - показуємо стару головну
    if not current_user.is_authenticated:
        return render_template("home.html")
    
    # === СТАТИСТИКА ===
    # 1. Рахуємо кількість договорів
    contracts_count = Contract.query.filter_by(user_id=current_user.id).count()
    
    # 2. Рахуємо загальну суму грошей (через SQL-функцію SUM)
    total_money = db.session.query(db.func.sum(Contract.amount)).filter_by(user_id=current_user.id).scalar() or 0
    
    # 3. Рахуємо події на сьогодні
    today = datetime.now().date()
    events_today = Event.query.filter_by(user_id=current_user.id, date=today).count()

    return render_template("home.html", 
                           contracts_count=contracts_count, 
                           total_money=total_money,
                           events_today=events_today)

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

# === [3] ФУНКЦІЯ СТВОРЕННЯ ДОГОВОРУ З ВІДПРАВКОЮ EMAIL ===
@app.route("/add_contract", methods=["GET", "POST"])
@login_required
def add_contract():
    if request.method == "POST":
        number = request.form["number"]
        client = request.form["client"]
        client_email = request.form["client_email"] # <--- Отримуємо email клієнта
        amount = float(request.form["amount"])
        start_date_str = request.form["start_date"]
        duration = int(request.form["duration"])
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        contract = Contract(
            number=number,
            client_name=client,
            client_email=client_email, # <--- Зберігаємо в БД
            amount=amount,
            start_date=start_date,
            duration_months=duration,
            user_id=current_user.id
        )
        db.session.add(contract)
        db.session.flush()

        monthly_payment = amount / duration
        
        for i in range(duration):
            payment_date = add_months(start_date, i)
            event = Event(
                title=f"Платіж: {client} ({i+1}/{duration})",
                description=f"Сума: {monthly_payment:.2f} грн. Договір №{number}.",
                date=payment_date,
                user_id=current_user.id,
                priority='high',
                event_type='payment',
                contract_id=contract.id
            )
            db.session.add(event)

        # --- ПОЧАТОК БЛОКУ ВІДПРАВКИ ---
        try:
            # Формуємо лист для клієнта
            msg = Message(f"✅ Ваш договір №{number} створено",
                          recipients=[client_email, current_user.email]) # Клієнту і копію менеджеру
            
            msg.body = f"""
            Шановний клієнте {client}!
            
            Ваш лізинговий договір успішно зареєстровано.
            
            ------------------------------------------------
            🔹 Номер договору: {number}
            🔹 Сума: {amount:,.2f} грн
            🔹 Термін: {duration} міс.
            🔹 Дата початку: {start_date}
            ------------------------------------------------
            
            Графік платежів сформовано.
            
            З повагою,
            Ваш персональний менеджер: {current_user.username}
            Compact Planner System
            """
            
            mail.send(msg)
            Analytics.log(f"Email sent to client: {client_email}")
            flash(f'Договір створено! Лист надіслано клієнту: {client_email}', 'success')
            
        except Exception as e:
            print(f"Помилка пошти: {e}") 
            Analytics.log(f"Email error: {e}")
            flash(f'Договір створено, але лист не надіслано (перевірте консоль).', 'warning')
        # --- КІНЕЦЬ БЛОКУ ВІДПРАВКИ ---

        db.session.commit()
        return redirect(url_for('current_month'))

    return render_template("add_contract.html")

# === [4] АНУЛЮВАННЯ ДОГОВОРУ З EMAIL ===
@app.route("/cancel_contract", methods=["GET", "POST"])
@login_required
def cancel_contract():
    if request.method == "POST":
        query = request.form["query"].strip()
        contract = Contract.query.filter(
            (Contract.user_id == current_user.id) & 
            ((Contract.number == query) | (Contract.client_name == query))
        ).first()

        if contract:
            deleted_info = f"{contract.number} ({contract.client_name})"
            target_email = contract.client_email # Запам'ятовуємо email перед видаленням
            
            # --- ВІДПРАВКА ЛИСТА ПРО АНУЛЮВАННЯ ---
            try:
                msg = Message(f"⚠️ Договір №{contract.number} АНУЛЬОВАНО",
                              recipients=[target_email, current_user.email])
                
                msg.body = f"""
                Шановний клієнте!
                
                Повідомляємо, що ваш договір №{contract.number} було розірвано/анульовано.
                Всі заплановані платежі скасовано.
                
                Якщо це помилка, зв'яжіться з вашим менеджером: {current_user.username}
                """
                mail.send(msg)
                print(f"Cancellation email sent to {target_email}")
            except Exception as e:
                print(f"Cancellation email failed: {e}")
            # -------------------------------------

            db.session.delete(contract)
            db.session.commit()
            Analytics.log(f"Contract cancelled: {deleted_info}")
            flash(f'Договір {deleted_info} анульовано. Клієнта повідомлено поштою.', 'danger')
            return redirect(url_for('current_month'))
        else:
            flash(f'Договір "{query}" не знайдено.', 'warning')

    return render_template("cancel_contract.html")

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
            flash('Раді вас бачити!', 'success')
            return redirect(url_for('current_month'))
        else:
            flash('Невірний логін або пароль.', 'danger')
    
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
            flash('Такий користувач вже існує', 'warning')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Такий email вже зареєстровано', 'warning')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        Analytics.log(f"New user: {username}")
        flash('Акаунт створено успішно!', 'success')
        return redirect(url_for('current_month'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви вийшли з системи.', 'info')
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

# === НОВЕ: СПИСОК ДОГОВОРІВ ТА ПОШУК ===
@app.route("/contracts")
@login_required
def all_contracts():
    query = request.args.get('q', '').strip()
    
    if query:
        # Шукаємо по номеру АБО по клієнту
        contracts = Contract.query.filter(
            (Contract.user_id == current_user.id) & 
            ((Contract.number.contains(query)) | (Contract.client_name.contains(query)))
        ).order_by(Contract.start_date.desc()).all()
    else:
        # Якщо пошуку немає - показуємо всі
        contracts = Contract.query.filter_by(user_id=current_user.id).order_by(Contract.start_date.desc()).all()
    
    return render_template("contracts.html", contracts=contracts, search_query=query)

# === НОВЕ: ШВИДКЕ АНУЛЮВАННЯ ПО ID ===
@app.route("/cancel/<int:contract_id>", methods=["POST"])
@login_required
def cancel_contract_id(contract_id):
    contract = Contract.query.filter_by(id=contract_id, user_id=current_user.id).first_or_404()
    
    deleted_info = f"{contract.number} ({contract.client_name})"
    target_email = contract.client_email
    
    # Відправка листа
    try:
        msg = Message(f"⚠️ Договір №{contract.number} АНУЛЬОВАНО",
                      recipients=[target_email, current_user.email])
        msg.body = f"Шановний клієнте! Ваш договір №{contract.number} анульовано менеджером."
        mail.send(msg)
    except Exception as e:
        print(f"Mail error: {e}")

    db.session.delete(contract)
    db.session.commit()
    
    flash(f'Договір {deleted_info} успішно анульовано.', 'info')
    return redirect(url_for('all_contracts'))

@app.route("/add", methods=["POST"])
@login_required
def add_event():
    title = request.form["title"]
    date_str = request.form["date"]
    desc = request.form.get("description", "")
    
    # 1. Retrieve the priority from the form. Default to 'medium' if missing.
    priority = request.form.get("priority", "medium") 

    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    event = Event(
        title=title,
        date=event_date,
        description=desc,
        user_id=current_user.id,
        # 2. Use the variable 'priority' instead of the string 'medium'
        priority=priority 
    )
    db.session.add(event)
    db.session.commit()
    
    flash('Подію успішно додано!', 'success')
    return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d")))

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
        flash('Подію оновлено!', 'success')
    return redirect(url_for("events_by_day", date=event.date.strftime("%Y-%m-%d")))

@app.route("/delete/<int:event_id>")
@login_required
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    
    if event:
        event_date = event.date
        db.session.delete(event)
        db.session.commit()
        flash('Подію видалено!', 'info')
        return redirect(url_for("events_by_day", date=event_date.strftime("%Y-%m-%d")))
    
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
         db.create_all()
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        pass