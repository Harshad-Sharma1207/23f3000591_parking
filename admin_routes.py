from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import db
from .models import ParkingLot, ParkingSpot, User, Reservation

admin = Blueprint('admin', __name__)

def is_admin():
    return current_user.is_authenticated and current_user.is_admin


# @admin.route('/dashboard')
# @login_required
# def admin_dashboard():
#     if not current_user.is_admin:
#         flash("Access denied.", "danger")
#         return redirect(url_for('user.user_dashboard'))

#     lots = ParkingLot.query.all()
#     admin = User.query.filter_by(is_admin=True).first()
#     return render_template('admin_dashboard.html', lots=lots, admin=admin)

@admin.route('/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('user.user_dashboard'))

    lots = ParkingLot.query.all()
    admin = User.query.filter_by(is_admin=True).first()
    reservations = Reservation.query.order_by(Reservation.parking_time.desc()).limit(10).all()

    # ➕ Add occupied_count to each lot
    for lot in lots:
        lot.occupied_count = sum(1 for spot in lot.spots if spot.status == 'O')

    return render_template('admin_dashboard.html', lots=lots, admin=admin, reservations=reservations)


@admin.route('/create_lot', methods=['GET', 'POST'])
@login_required
def create_lot():
    if not is_admin():
        return redirect(url_for('main.index'))


    if request.method == 'POST':
        # name = request.form['name']
        # address = request.form['address']
        # pincode = request.form['pincode']  # ❌ throws error if 'pincode' missing
        name = request.form.get('name') 
        address = request.form.get('address') 
        pincode = request.form.get('pincode')  # ✅ returns None if missing

        price = float(request.form['price'])
        max_spots = int(request.form['max_spots'])

        lot = ParkingLot(name=name, address=address, pincode=pincode, price=price, max_spots=max_spots)
        db.session.add(lot)
        db.session.commit()

        for _ in range(max_spots):
            spot = ParkingSpot(lot_id=lot.id, status='A')
            db.session.add(spot)
        db.session.commit()

        flash('Parking lot created successfully.')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('create_lot.html')

@admin.route('/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def edit_lot(lot_id):
    if not is_admin():
        return redirect(url_for('main.index'))

    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        # lot.name = request.form['name']
        # lot.address = request.form['address']
        new_max_spots = int(request.form['max_spots'])

        if new_max_spots > lot.max_spots:
            flash(f"You cannot increase beyond the original spot limit ({lot.max_spots}).", "danger")
            return redirect(url_for('admin.edit_lot', lot_id=lot.id))

        lot.pincode = request.form['pincode']
        lot.price = float(request.form['price'])
        new_max_spots = int(request.form['max_spots'])

        existing_spots = len(lot.spots)
        if new_max_spots > existing_spots:
            for _ in range(new_max_spots - existing_spots):
                spot = ParkingSpot(lot_id=lot.id, status='A')
                db.session.add(spot)
        elif new_max_spots < existing_spots:
            available_spots = [s for s in lot.spots if s.status == 'A']
            if len(available_spots) < (existing_spots - new_max_spots):
                flash('Cannot reduce spots: too many are occupied.')
                return redirect(url_for('admin.edit_lot', lot_id=lot.id))
            for s in available_spots[:existing_spots - new_max_spots]:
                db.session.delete(s)

        lot.max_spots = new_max_spots
        db.session.commit()
        flash('Parking lot updated.')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)

@admin.route('/delete_lot/<int:lot_id>')
@login_required
def delete_lot(lot_id):
    if not is_admin():
        return redirect(url_for('main.index'))

    lot = ParkingLot.query.get_or_404(lot_id)
    occupied = any(s.status == 'O' for s in lot.spots)
    if occupied:
        flash('Cannot delete: some spots are still occupied.')
        return redirect(url_for('admin.admin_dashboard'))

    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted.')
    return redirect(url_for('admin.admin_dashboard'))

@admin.route('/view_users')
@login_required
def view_users():
    if not is_admin():
        return redirect(url_for('main.index'))
    users = User.query.filter_by(is_admin=False).all()
    return render_template('view_users.html', users=users)

@admin.route('/lot_status/<int:lot_id>')
@login_required
def lot_status(lot_id):
    if not is_admin():
        return redirect(url_for('main.index'))
    lot = ParkingLot.query.get_or_404(lot_id)
    return render_template('lot_status.html', lot=lot, spots=lot.spots)


@admin.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if not is_admin():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        from werkzeug.security import check_password_hash, generate_password_hash

        current = request.form['current_password']
        new = request.form['new_password']
        confirm = request.form['confirm_password']

        if not check_password_hash(current_user.password, current):
            flash('Current password is incorrect.')
            return redirect(url_for('admin.change_password'))

        if new != confirm:
            flash('New passwords do not match.')
            return redirect(url_for('admin.change_password'))

        current_user.password = generate_password_hash(new, method='pbkdf2:sha256')
        db.session.commit()
        flash('Password updated successfully.')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('change_password.html')

@admin.route('/earnings')
@login_required
def total_earnings():
    if not is_admin():
        return redirect(url_for('main.index'))

    reservations = Reservation.query.all()
    total = 0
    for r in reservations:
        if r.leaving_time:  # ✅ correct field
            start = datetime.strptime(r.parking_time, "%Y-%m-%d %H:%M:%S.%f")
            end = datetime.strptime(r.leaving_time, "%Y-%m-%d %H:%M:%S.%f")

            duration = (end - start).total_seconds() / 3600
            price = r.cost_per_unit
            total += price * duration
    return render_template('earnings.html', total=round(total, 2))

@admin.route('/delete_reservations', methods=['POST'])
@login_required
def delete_reservations():
    if not is_admin():
        return redirect(url_for('main.index'))

    # Delete all reservation entries
    Reservation.query.delete()
    db.session.commit()
    flash('All reservation history has been deleted.', 'success')
    return redirect(url_for('admin.admin_dashboard'))
