from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from flask_mail import Message
from flask_login import login_required, current_user 
from . import db, mail 
from .models import Appointment, User
import heapq

# --- PRICES ---
SERVICE_PRICES = {
    "AC Repair": 60,
    "Plumbing": 45,
    "Electrician": 50,
    "House Cleaning": 30,
    "Car Wash": 15
}

main = Blueprint('main', __name__)

# --- REGISTRATION ---
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash("Username already taken!", "error")
            return redirect(url_for('main.register'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "error")
            return redirect(url_for('main.register'))

        is_admin_user = "ADMIN" in username
        new_user = User(username=username, email=email, password_hash=password, is_admin=is_admin_user)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created! Please login.", "success")
        return redirect(url_for('main.login'))
    return render_template('register.html')

# --- LOGIN ---
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == password:
            session['user_logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.home'))
        else:
            flash("Wrong username or password!", "error")
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

# --- DASHBOARD ---
@main.route('/')
def home():
    if not session.get('user_logged_in'): return redirect(url_for('main.login'))  

    user_id = session.get('user_id')
    current_user = User.query.get(user_id)
    
    if current_user is None:
        session.clear()
        return redirect(url_for('main.login'))

    search_query = request.args.get('q')
    status_filter = request.args.get('status')

    if current_user.is_admin:
        query = Appointment.query
        page_title = "Admin Dashboard"
    else:
        query = Appointment.query.filter_by(user_id=user_id)
        page_title = "My Appointments"

    if search_query:
        if current_user.is_admin:
            query = query.join(User).filter(
                (Appointment.service_name.contains(search_query)) | 
                (User.username.contains(search_query))
            )
        else:
            query = query.filter(Appointment.service_name.contains(search_query))

    if status_filter:
        query = query.filter_by(status=status_filter)

    appointments = query.all()

    # Stats Logic
    if current_user.is_admin:
        stats_query = Appointment.query
    else:
        stats_query = Appointment.query.filter_by(user_id=user_id)

    total_count = stats_query.count()
    pending_count = stats_query.filter_by(status='pending').count()
    completed_count = stats_query.filter_by(status='Completed').count()
    
    revenue = 0
    completed_jobs = stats_query.filter_by(status='Completed').all()
    for job in completed_jobs:
        revenue += job.price

    return render_template('index.html', 
                           appointments=appointments, 
                           username=current_user.username, 
                           title=page_title,
                           total=total_count,
                           pending=pending_count,
                           completed=completed_count,
                           revenue=revenue,
                           is_admin=current_user.is_admin)

# --- BOOKING ---
@main.route('/book_form', methods=['POST'])
def book_form():
    if not session.get('user_logged_in'): return redirect(url_for('main.login'))
    
    user_id = session.get('user_id')
    service = request.form.get('service')
    time_str = request.form.get('time')

    try:
        clean_time_str = time_str[:16]
        appt_time = datetime.strptime(clean_time_str, '%Y-%m-%dT%H:%M')
        
        if appt_time < datetime.now():
            flash("Error: You cannot book a date in the past!", "error")
            return redirect(url_for('main.home'))
        
        cost = SERVICE_PRICES.get(service, 0)
        new_appt = Appointment(user_id=user_id, service_name=service, appointment_time=appt_time, price=cost)
        db.session.add(new_appt)
        db.session.commit()

        # Email Notification
        try:
            user = User.query.get(user_id)
            if user.email:
                msg = Message('Booking Confirmed', sender='noreply@demo.com', recipients=[user.email])
                msg.body = f"Hello {user.username}, your booking for {service} is confirmed!"
                mail.send(msg)
                flash("Appointment booked! Email sent.", "success")
        except Exception:
            flash("Appointment booked, but email failed.", "warning")

    except ValueError:
        flash("Invalid Date Format!", "error")

    return redirect(url_for('main.home'))

# --- ACTIONS ---
@main.route('/complete/<int:id>')
def complete_appointment(id):
    appt = Appointment.query.get(id)
    if appt:
        appt.status = 'Completed'
        db.session.commit()
    return redirect(url_for('main.home'))

@main.route('/delete/<int:id>')
def delete_appointment(id):
    appt = Appointment.query.get(id)
    if appt:
        db.session.delete(appt)
        db.session.commit()
    return redirect(url_for('main.home'))

# --- EDIT ---
@main.route('/edit/<int:id>', methods=['GET'])
def edit_view(id):
    if not session.get('user_logged_in'): return redirect(url_for('main.login'))
    appt = Appointment.query.get(id)
    return render_template('edit.html', appointment=appt)

@main.route('/update/<int:id>', methods=['POST'])
def update_appointment(id):
    appt = Appointment.query.get(id)
    new_service = request.form.get('service')
    new_time_str = request.form.get('time')
    try:
        clean_time_str = new_time_str[:16]
        new_time = datetime.strptime(clean_time_str, '%Y-%m-%dT%H:%M')
        appt.service_name = new_service
        appt.appointment_time = new_time
        db.session.commit()
        flash("Updated Successfully!", "success")
    except ValueError:
        flash("Invalid Date!", "error")
    return redirect(url_for('main.home'))

# --- RATING & TICKET ---
@main.route('/ticket/<int:id>')
def view_ticket(id):
    if not session.get('user_logged_in'): return redirect(url_for('main.login'))
    appt = Appointment.query.get(id)
    return render_template('ticket.html', appointment=appt)

@main.route('/rate/<int:id>')
def rate_view(id):
    if not session.get('user_logged_in'): return redirect(url_for('main.login'))
    appt = Appointment.query.get(id)
    return render_template('rate.html', appointment=appt)

@main.route('/save_rating/<int:id>', methods=['POST'])
def save_rating(id):
    appt = Appointment.query.get(id)
    appt.rating = request.form.get('stars')
    appt.review = request.form.get('review')
    db.session.commit()
    return redirect(url_for('main.home'))

# --- PRIORITY QUEUE (HEAP) ---
@main.route('/priority')
def priority_view():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)
    if not current_user.is_admin:
        return redirect(url_for('main.home'))
    
    pending_appts = Appointment.query.filter_by(status='pending').all()
    priority_queue = []
    for appt in pending_appts:
        heapq.heappush(priority_queue, (appt.appointment_time, appt.id, appt))
    
    sorted_urgent_jobs = []
    while priority_queue:
        _, _, appt = heapq.heappop(priority_queue) 
        sorted_urgent_jobs.append(appt)

    return render_template('index.html', appointments=sorted_urgent_jobs, username=current_user.username, 
                           title="Urgent Jobs (Priority Queue)", total=len(sorted_urgent_jobs), 
                           pending=len(sorted_urgent_jobs), completed=0, revenue=0, is_admin=True)

# --- 💰 PAYMENT SYSTEM 💰 ---

@main.route('/pay/<int:id>')
def payment_page(id):
    if not session.get('user_logged_in'): return redirect(url_for('main.login'))
    appt = Appointment.query.get(id)
    
    # YOUR UPI DETAILS (Edit these!)
    my_upi_id = "6354540114@fam" 
    my_name = "QuickServe_Admin"
    
    upi_link = f"upi://pay?pa={my_upi_id}&pn={my_name}&am={appt.price}&cu=INR"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={upi_link}"

    return render_template('payment.html', appointment=appt, qr_code=qr_code_url)

@main.route('/process_payment/<int:id>', methods=['POST'])
def process_payment(id):
    appt = Appointment.query.get(id)
    trans_id = request.form.get('transaction_id')
    
    # 1. Validation: Check Length
    if len(trans_id) < 8:
        flash("Error: Transaction ID is too short!", "error")
        return redirect(url_for('main.payment_page', id=id))

    # 2. Validation: Check Duplicate
    existing_payment = Appointment.query.filter_by(transaction_id=trans_id).first()
    if existing_payment:
        flash("Error: This Transaction ID has already been used!", "error")
        return redirect(url_for('main.payment_page', id=id))

    # Mark as PENDING VERIFICATION
    appt.payment_status = 'Verification Pending'
    appt.transaction_id = trans_id
    db.session.commit()
    
    flash("Payment recorded! Waiting for Admin approval.", "info")
    return redirect(url_for('main.home'))

@main.route('/approve_payment/<int:id>')
def approve_payment(id):
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)
    if not current_user.is_admin:
        flash("Only Admin can approve payments!", "error")
        return redirect(url_for('main.home'))

    appt = Appointment.query.get(id)
    appt.payment_status = 'Paid'     
    appt.status = 'In Progress'      
    db.session.commit()
    
    flash(f"Payment Verified for Appointment #{id}", "success")
    return redirect(url_for('main.home'))