from . import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Float, nullable=False) 
    reservations = db.relationship('Reservation', backref='user')



class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    price = db.Column(db.Float)
    max_spots = db.Column(db.Integer)
    spots = db.relationship('ParkingSpot',
                            backref='lot',
                            cascade="all, delete")


class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(1),
                    default='A')  # A = Available, O = Occupied
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'))
    reservation = db.relationship('Reservation', backref='spot', uselist=False)


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    parking_time = db.Column(db.String(100))
    leaving_time = db.Column(db.String(100))
    cost_per_unit = db.Column(db.Float)

    ###
    name = db.Column(db.String(100))
    vehicle_type = db.Column(db.String(50))
    vehicle_number = db.Column(db.String(50))
    contact = db.Column(db.String(50))
