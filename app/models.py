from . import db, login_manager
from flask_login import UserMixin
from datetime import datetime

# --- USER LOADER (Required for Login) ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- DATABASE TABLES ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')
    price = db.Column(db.Float, default=0.0)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Rating
    rating = db.Column(db.Integer, nullable=True)
    review = db.Column(db.Text, nullable=True)
    
    # Payment Columns
    payment_status = db.Column(db.String(30), default='Unpaid') # Unpaid, Verification Pending, Paid
    transaction_id = db.Column(db.String(50), nullable=True)    # Store UTR