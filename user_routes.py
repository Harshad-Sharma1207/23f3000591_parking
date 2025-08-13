from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from .models import ParkingLot, ParkingSpot, Reservation, User
import pytz


user = Blueprint('user', __name__)


# ✅ Helper function to safely parse datetime
def safe_parse_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")


# ✅ Dashboard: shows lots + history of reservations
@user.route('/dashboard')
@login_required
def user_dashboard():
    lots = ParkingLot.query.all()
    reservations = Reservation.query.filter_by(
        user_id=current_user.id).order_by(
            Reservation.parking_time.desc()).all()

    total_cost = 0
    india_tz = pytz.timezone("Asia/Kolkata")

    for r in reservations:
        r.parking_time = safe_parse_datetime(r.parking_time).replace(tzinfo=pytz.UTC).astimezone(india_tz)

        if r.leaving_time:
            r.leaving_time = safe_parse_datetime(r.leaving_time).replace(tzinfo=pytz.UTC).astimezone(india_tz)
            duration = (r.leaving_time - r.parking_time).total_seconds() / 3600
            r.cost = round(duration * r.cost_per_unit, 2)
            total_cost += r.cost
        else:
            r.cost = None

    return render_template('user_dashboard.html',
                           lots=lots,
                           reservations=reservations,
                           total_cost=round(total_cost, 2))


# ✅ Reserve first available spot
@user.route('/reserve')
@login_required
def reserve_any_spot():
    lots = ParkingLot.query.all()
    for lot in lots:
        spot = next((s for s in lot.spots if s.status == 'A'), None)
        if spot:
            spot.status = 'O'
            reservation = Reservation(
                spot_id=spot.id,
                user_id=current_user.id,
                parking_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                cost_per_unit=lot.price)
            db.session.add(reservation)
            db.session.commit()
            flash(f"✅ Spot reserved in lot '{lot.name}' (Spot ID: {spot.id})",
                  'success')
            return redirect(url_for('user.user_dashboard'))

    flash("❌ All parking spots are currently occupied.", "danger")
    return redirect(url_for('user.user_dashboard'))


@user.route('/release')
@login_required
def show_release_options():
    active_reservations = Reservation.query.filter_by(
        user_id=current_user.id, leaving_time=None).all()

    if not active_reservations:
        flash("❌ You do not have any active reservations to release.", "danger")
        return redirect(url_for('user.user_dashboard'))

    return render_template("release_selection.html", reservations=active_reservations)

@user.route('/release/<int:reservation_id>')
@login_required
def release_specific_reservation(reservation_id):
    reservation = Reservation.query.filter_by(
        id=reservation_id, user_id=current_user.id, leaving_time=None).first()

    if not reservation:
        flash("❌ Invalid or already released reservation.", "danger")
        return redirect(url_for('user.user_dashboard'))

    reservation.leaving_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reservation.spot.status = 'A'

    # Calculate cost
    start = datetime.strptime(reservation.parking_time, "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(reservation.leaving_time, "%Y-%m-%d %H:%M:%S")
    duration = (end - start).total_seconds() / 3600
    cost = round(duration * reservation.cost_per_unit, 2)

    db.session.commit()

    return render_template("bill.html", cost=cost, reservation_id=reservation.id)



# ✅ Show parking summary
@user.route('/summary')
@login_required
def parking_summary():
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template("parking_summary.html",
                           title="My Parking Summary",
                           reservations=reservations)


# ✅ User account settings (update username/password)
@user.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        new_username = request.form['username']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not check_password_hash(current_user.password, current_password):
            flash('❌ Incorrect current password.', 'danger')
            return redirect(url_for('user.account'))

        if new_password != confirm_password:
            flash('❌ New passwords do not match.', 'warning')
            return redirect(url_for('user.account'))

        current_user.username = new_username
        if new_password:
            current_user.password = generate_password_hash(new_password)

        db.session.commit()
        flash('✅ Account updated successfully.', 'success')
        return redirect(url_for('user.user_dashboard'))

    return render_template('account.html')
    

@user.route('/delete_history', methods=['POST'])
@login_required
def delete_history():
    past_reservations = Reservation.query.filter_by(
        user_id=current_user.id).filter(
            Reservation.leaving_time != None).all()
    for r in past_reservations:
        db.session.delete(r)
    db.session.commit()
    flash("✅ Reservation history deleted successfully.", "success")
    return redirect(url_for('user.user_dashboard'))


@user.route('/confirm_payment', methods=['POST'])
@login_required
def confirm_payment():
    cost = float(request.form['cost'])
    reservation_id = int(request.form['reservation_id'])

    if current_user.balance < cost:
        flash("❌ Insufficient balance. Please top up.", "danger")
        return redirect(url_for('user.user_dashboard'))

    # Deduct from user
    current_user.balance -= cost

    # Credit to admin
    admin_user = User.query.filter_by(is_admin=True).first()
    if admin_user:
        admin_user.balance += cost

    db.session.commit()
    flash(f"✅ Payment of ₹{cost} successful! Your updated balance is ₹{round(current_user.balance, 2)}.", "success")
    return redirect(url_for('user.user_dashboard'))

@user.route('/reserve/<int:lot_id>', methods=['POST'])
@login_required
def reserve_spot_in_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spot = next((s for s in lot.spots if s.status == 'A'), None)

    if not spot:
        flash("❌ All spots in this lot are occupied.", "danger")
        return redirect(url_for('user.user_dashboard'))

    # Get data from form
    name = request.form.get('name')
    vehicle_type = request.form.get('vehicle_type')
    vehicle_number = request.form.get('vehicle_number')
    contact = request.form.get('contact')

    # You can store this in Reservation table (see Step 3)
    reservation = Reservation(
        spot_id=spot.id,
        user_id=current_user.id,
        parking_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        cost_per_unit=lot.price,
        name=name,
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number,
        contact=contact
    )

    spot.status = 'O'
    db.session.add(reservation)
    db.session.commit()

    flash(f"✅ Spot reserved in lot '{lot.name}' (Spot ID: {spot.id})", 'success')
    return redirect(url_for('user.user_dashboard'))
