from flask import current_app as app, jsonify, request, render_template, redirect, url_for, session, flash
from backend.models import db, User, ParkingLot, ParkingSpot, Reservation
from datetime import datetime, timezone
from sqlalchemy import or_
import pytz

# Create a Blueprint

def get_ist_now():
    """Get current time in IST timezone"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def utc_to_ist(utc_dt):
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None
    
    # If datetime is naive (no timezone info), assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    ist = pytz.timezone('Asia/Kolkata')
    return utc_dt.astimezone(ist)

def format_datetime_ist(dt):
    """Format datetime in IST for display"""
    if dt is None:
        return None
    
    # Convert to IST if it's not already
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    
    ist = pytz.timezone('Asia/Kolkata')
    ist_dt = dt.astimezone(ist)
    
    return ist_dt.strftime('%Y-%m-%d %H:%M:%S')

@app.route("/user/search_parking_lots", methods=['GET'])
def user_search_parking_lots():
    """Search for available parking lots based on name, address or pincode"""
    search_term = request.args.get('q', '')
    
    # Search in multiple fields with partial matching
    parking_lots = ParkingLot.query.filter(
        or_(
            ParkingLot.prime_location_name.ilike(f'%{search_term}%'),
            ParkingLot.address.ilike(f'%{search_term}%'),
            ParkingLot.pincode.ilike(f'%{search_term}%'),
            ParkingLot.price_per_hour.ilike(f'%{search_term}%')
        )
    ).all()
    
    result = []
    for lot in parking_lots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        occupied_count = sum(1 for spot in spots if spot.status == 'O')
        available_count = lot.maximum_number_of_spots - occupied_count
        
        result.append({
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pincode': lot.pincode, 
            'price_per_hour': lot.price_per_hour,
            'max_spots': lot.maximum_number_of_spots,
            'occupied': occupied_count,
            'available': available_count
        })
    
    return jsonify(result)

@app.route("/user/available_spots", methods=['GET'])
def user_available_spots():
    lot_id = request.args.get('lot_id')
    if not lot_id:
        return jsonify({'error': 'Lot ID is required'}), 400

    # Get ALL spots, not just available ones
    all_spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()

    lot = ParkingLot.query.get(lot_id)
    if not lot:
        return jsonify({'error': 'Parking lot not found'}), 404

    result = []
    for spot in all_spots:
        result.append({
            'id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'price_per_hour': lot.price_per_hour,
            'status': spot.status  # A or O
        })

    return jsonify(result)

@app.route("/user/book_spot", methods=['POST'])
def book_parking_spot():
    """Book a parking spot"""
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    user_id = session['user_id']
    active = Reservation.query.filter_by(user_id=user_id, status='active').first()
    if active:
        return jsonify({
            'error': 'You already have an active reservation. Please release it before booking a new one.'
        }), 400
    
    data = request.json
    spot_id = data.get('spot_id')
    
    if not spot_id:
        return jsonify({'error': 'Spot ID is required'}), 400
    
    # Check if spot exists and is available
    spot = ParkingSpot.query.get(spot_id)
    if not spot:
        return jsonify({'error': 'Parking spot not found'}), 404
    
    if spot.status != 'A':
        return jsonify({'error': 'Parking spot is already occupied'}), 400
    
    # Get the parking lot for pricing information
    lot = ParkingLot.query.get(spot.lot_id)
    if not lot:
        return jsonify({'error': 'Associated parking lot not found'}), 404
    
    try:
        # Create reservation with current IST time converted to UTC for storage
        current_ist = get_ist_now()
        current_utc = current_ist.astimezone(timezone.utc).replace(tzinfo=None)
        
        reservation = Reservation(
            spot_id=spot_id,
            user_id=session['user_id'],
            parking_timestamp=current_utc,  # Store as UTC in database
            status='active'
        )
        
        # Update spot status to occupied
        spot.status = 'O'
        
        # Add and commit in proper order
        db.session.add(reservation)
        db.session.flush()  # This ensures the reservation gets an ID
        db.session.commit()
        
        print(f"DEBUG: Created reservation ID {reservation.id}")
        print(f"DEBUG: IST time: {current_ist}")
        print(f"DEBUG: UTC stored: {current_utc}")
        
        return jsonify({
            'message': 'Parking spot booked successfully',
            'reservation_id': reservation.id,
            'spot_number': spot.spot_number,
            'lot_name': lot.prime_location_name,
            'price_per_hour': float(lot.price_per_hour),
            'parking_timestamp': format_datetime_ist(current_utc)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in book_spot: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route("/user/release_spot", methods=['POST'])
def release_parking_spot():
    """Release a parking spot and complete the reservation"""
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.json
    reservation_id = data.get('reservation_id')
    
    if not reservation_id:
        return jsonify({'error': 'Reservation ID is required'}), 400
    
    try:
        # Find the active reservation
        reservation = Reservation.query.filter_by(
            id=reservation_id, 
            user_id=session['user_id'],
            status='active'
        ).first()
        
        if not reservation:
            return jsonify({'error': 'Active reservation not found'}), 404
        
        # Get the associated spot
        spot = ParkingSpot.query.get(reservation.spot_id)
        if not spot:
            return jsonify({'error': 'Associated parking spot not found'}), 404
        
        # Get the parking lot for pricing information
        lot = ParkingLot.query.get(spot.lot_id)
        if not lot:
            return jsonify({'error': 'Associated parking lot not found'}), 404
        
        # Calculate duration and cost
        current_ist = get_ist_now()
        current_utc = current_ist.astimezone(timezone.utc).replace(tzinfo=None)
        
        # Calculate duration in hours
        parking_start = reservation.parking_timestamp
        duration_seconds = (current_utc - parking_start).total_seconds()
        duration_hours = max(duration_seconds / 3600, 0.1)  # Minimum 0.1 hours (6 minutes)
        parking_cost = duration_hours * float(lot.price_per_hour)
        
        # Update reservation
        reservation.leaving_timestamp = current_utc
        reservation.parking_cost = round(parking_cost, 2)
        reservation.status = 'completed'
        
        # Update spot status to available
        spot.status = 'A'
        
        # Commit changes
        db.session.commit()
        
        print(f"DEBUG: Released reservation ID {reservation.id}")
        print(f"DEBUG: Parking start: {parking_start}")
        print(f"DEBUG: Leaving time: {current_utc}")
        print(f"DEBUG: Duration: {duration_hours:.2f} hours")
        print(f"DEBUG: Cost: ₹{parking_cost:.2f}")
        
        return jsonify({
            'message': 'Parking spot released successfully',
            'reservation_id': reservation.id,
            'duration_hours': round(duration_hours, 2),
            'cost': round(parking_cost, 2),
            'parking_timestamp': format_datetime_ist(parking_start),
            'leaving_timestamp': format_datetime_ist(current_utc),
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'pay_and_checkout': True
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in release_spot: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route("/user/active_reservation", methods=['GET'])
def get_active_reservation():
    """Get active parking reservation for the logged-in user"""
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    user_id = session['user_id']
    
    try:
        # Find active reservation
        reservation = Reservation.query.filter_by(
            user_id=user_id,
            status='active'
        ).first()
        
        if not reservation:
            return jsonify({'active_reservation': False})
        
        # Check if parking_timestamp exists
        if not reservation.parking_timestamp:
            print(f"WARNING: Reservation {reservation.id} has no parking_timestamp")
            return jsonify({'error': 'Invalid reservation data'}), 500
        
        # Get spot information
        spot = ParkingSpot.query.get(reservation.spot_id)
        if not spot:
            return jsonify({'error': 'Associated parking spot not found'}), 404
        
        # Get lot information
        lot = ParkingLot.query.get(spot.lot_id)
        if not lot:
            return jsonify({'error': 'Associated parking lot not found'}), 404
        
        # Calculate current duration and cost for display
        current_ist = get_ist_now()
        current_utc = current_ist.astimezone(timezone.utc).replace(tzinfo=None)
        
        parking_start = reservation.parking_timestamp
        duration_seconds = (current_utc - parking_start).total_seconds()
        duration_hours = max(duration_seconds / 3600, 0)
        current_cost = duration_hours * float(lot.price_per_hour)
        
        result = {
            'active_reservation': True,
            'reservation_id': reservation.id,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'parking_timestamp': format_datetime_ist(parking_start),
            'duration_hours': round(duration_hours, 2),
            'current_cost': round(current_cost, 2),
            'price_per_hour': float(lot.price_per_hour)
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR in get_active_reservation: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route("/user/parking_history", methods=['GET'])
def get_parking_history():
    """Get parking history for the logged-in user"""
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    user_id = session['user_id']
    
    # Optional status filter
    status = request.args.get('status', None)
    
    query = Reservation.query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)
    
    # Order by most recent first
    reservations = query.order_by(Reservation.parking_timestamp.desc()).all()
    
    result = []
    for reservation in reservations:
        # Get spot information
        spot = ParkingSpot.query.get(reservation.spot_id)
        if not spot:
            continue
        
        # Get lot information
        lot = ParkingLot.query.get(spot.lot_id)
        if not lot:
            continue
        
        result.append({
            'id': reservation.id,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'parking_timestamp': format_datetime_ist(reservation.parking_timestamp),
            'leaving_timestamp': format_datetime_ist(reservation.leaving_timestamp) if reservation.leaving_timestamp else None,
            'status': reservation.status,
            'parking_cost': reservation.parking_cost,
            'price_per_hour': float(lot.price_per_hour)
        })
    
    return jsonify(result)

@app.route('/payment')
def payment_page():
    return render_template('payment.html')

# Route for the user dashboard page