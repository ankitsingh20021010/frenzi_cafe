from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from flask_migrate import Migrate
import pytz
from twilio_config import send_sms  # ✅ Import Twilio SMS function

app = Flask(__name__)

app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///frenzi_cafe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ✅ Get India Time
def get_india_time():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

# 👤 Employee Model
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)

# 🍽️ Order Model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(20))
    items = db.Column(db.String(200))
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=get_india_time)

# 🧳 History Model
class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(20))
    items = db.Column(db.String(200))
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=get_india_time)
    created_by = db.Column(db.String(80))

# 🔐 Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        employee = Employee.query.filter_by(username=username, password=password).first()
        if employee:
            if not employee.is_approved:
                flash("Your account is pending admin approval.", "warning")
                return redirect(url_for('login'))
            session['employee'] = True
            session['username'] = employee.username
            return redirect(url_for('dashboard'))
        flash("Invalid credentials!", "danger")
        return redirect(url_for('login'))
    return render_template('login.html')

# 👤 Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if Employee.query.filter_by(username=username).first():
            flash("Username already exists!", "warning")
            return redirect(url_for('register'))
        new_emp = Employee(username=username, password=password, is_approved=False)
        db.session.add(new_emp)
        db.session.commit()
        flash("Account created. Wait for admin approval.", "info")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
def home():
    return redirect(url_for('login'))

# 📊 Dashboard
@app.route('/dashboard')
def dashboard():
    if 'employee' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', tables=range(1, 11))

# 🍽️ Table Detail
@app.route('/table/<int:table_id>', methods=['GET', 'POST'])
def table_detail(table_id):
    if 'employee' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        item = request.form.get('item')
        price = request.form.get('price')
        if item and price:
            order = Order(table_number=str(table_id), items=item, amount=float(price))
            db.session.add(order)
            db.session.commit()
            flash("Item added!", "success")
        return redirect(url_for('table_detail', table_id=table_id))

    orders = Order.query.filter_by(table_number=str(table_id)).order_by(Order.timestamp).all()
    total = sum(o.amount for o in orders)
    return render_template('table_detail.html', table_id=table_id, orders=orders, total=total)

# ✅ Clear Table and Save to History
@app.route('/clear_table/<int:table_id>', methods=['POST'])
def clear_table(table_id):
    if 'employee' not in session:
        return redirect(url_for('login'))

    orders = Order.query.filter_by(table_number=str(table_id)).all()

    for order in orders:
        history = History(
            table_number=order.table_number,
            items=order.items,
            amount=order.amount,
            timestamp=order.timestamp,
            created_by=session.get('username')
        )
        db.session.add(history)
        db.session.delete(order)

    db.session.commit()
    flash(f"Table {table_id} cleared and history saved!", "success")
    return redirect(url_for('dashboard'))

# 💵 Bill Generation
@app.route('/bill', methods=['POST'])
def bill():
    if 'employee' not in session:
        return redirect(url_for('login'))

    table = request.form['table_number']
    orders = Order.query.filter_by(table_number=table).all()
    total = sum(order.amount for order in orders)

    detailed_orders = []
    for order in orders:
        items = [i.strip() for i in order.items.split(',') if i.strip()]
        price_per_item = order.amount / len(items) if items else 0
        for item in items:
            detailed_orders.append({'item_name': item, 'amount': round(price_per_item, 2)})

    return render_template('bill.html', orders=detailed_orders, total=total, table=table, datetime=get_india_time())

# ✅ Send SMS
@app.route('/send-sms', methods=['POST'])
def send_sms_route():
    if 'employee' not in session:
        return redirect(url_for('login'))

    phone_number = request.form['phone_number']
    table_number = request.form['table_number']
    total = request.form['total']

    message = f"🍽️ Frenzi Café\nTable: {table_number}\nTotal Bill: ₹{total}\nThank you! 🙏"
    try:
        send_sms(phone_number, message)
        flash("SMS sent successfully!", "success")
    except Exception as e:
        flash(f"Failed to send SMS: {str(e)}", "danger")

    return redirect(url_for('dashboard'))

# 📜 View History
@app.route('/history')
def history():
    if 'employee' not in session:
        return redirect(url_for('login'))

    filter_option = request.args.get('filter', 'all')
    now = get_india_time()

    if filter_option == 'today':
        start_time = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
    elif filter_option == 'last_week':
        start_time = now - timedelta(days=7)
    elif filter_option == 'last_month':
        start_time = now - timedelta(days=30)
    else:
        start_time = None

    if start_time:
        orders = History.query.filter(History.timestamp >= start_time).order_by(History.timestamp.desc()).all()
    else:
        orders = History.query.order_by(History.timestamp.desc()).all()

    total = sum(order.amount for order in orders)
    return render_template('history.html', orders=orders, selected_filter=filter_option, total=total)

# 💵 Sales Summary
@app.route('/sales')
def sales():
    today = date.today()
    total_sales = db.session.query(db.func.sum(Order.amount)).scalar()
    if total_sales is None:
        total_sales = 0
    return render_template('sales.html', total_sales=total_sales, today=today.strftime("%d-%m-%Y"))

# 👥 Admin Employees
@app.route('/admin/employees')
def employee_list():
    if 'employee' not in session or session.get('username') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))
    employees = Employee.query.filter_by(is_approved=True).all()
    return render_template('employee_list.html', employees=employees)

# ✅ Admin Approves Users Page
@app.route('/approve-users')
def approve_users():
    if 'employee' not in session or session.get('username') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))
    users = Employee.query.filter_by(is_approved=False).all()
    return render_template('approve_users.html', users=users)

# ✅ Admin Approves Users
@app.route('/approve', methods=['POST'])
def approve():
    if 'employee' not in session or session.get('username') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    user_id = request.form.get('user_id')
    if user_id:
        user = Employee.query.get(int(user_id))
        if user and not user.is_approved:
            user.is_approved = True
            db.session.commit()
            flash(f"User '{user.username}' approved!", "success")

    return redirect(url_for('approve_users'))

# ❌ Admin Rejects Users
@app.route('/reject', methods=['POST'])
def reject():
    if 'employee' not in session or session.get('username') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    user_id = request.form.get('user_id')
    if user_id:
        user = Employee.query.get(int(user_id))
        if user and not user.is_approved:
            db.session.delete(user)
            db.session.commit()
            flash(f"User '{user.username}' has been rejected and removed.", "success")
        else:
            flash("User not found or already approved.", "warning")

    return redirect(url_for('approve_users'))

# ❌ Admin Deletes Approved User
@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'employee' not in session or session.get('username') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    user = Employee.query.get(user_id)
    if user and user.username != 'admin':
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{user.username}' deleted successfully.", "success")
    else:
        flash("Cannot delete admin or invalid user.", "warning")

    return redirect(url_for('employee_list'))

# 🔓 Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ✅ Create Tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)