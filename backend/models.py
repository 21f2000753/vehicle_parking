from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # user/admin
    address = db.Column(db.String(300), nullable=False)
    pincode = db.Column(db.String(8), nullable=False)

    reservations = db.relationship('Reservation', backref='user', lazy=True)


class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(120), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(300), nullable=False)
    pincode = db.Column(db.String(8), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)

    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # A = Available, O = Occupied
    spot_number = db.Column(db.String(20), nullable=False)  # Optional: helpful for UI

    reservations = db.relationship('Reservation', backref='spot', lazy=True)


class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)  # Could be calculated later

    # Optional: status to mark active or completed reservations
    status = db.Column(db.String(20), default='active')
