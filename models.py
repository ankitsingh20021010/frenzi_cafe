from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Employee Table - For login/registration
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # You can hash this later for security
    is_approved = db.Column(db.Boolean, default=False)  # New field: admin approval

# Order Table - For table-wise orders
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(10), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending / Paid
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

# Function to initialize database
def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
