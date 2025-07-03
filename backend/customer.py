from flask import current_app as app, jsonify, request, render_template, redirect, url_for, session, flash
from backend.models import db, User, ParkingLot, ParkingSpot, Reservation
from datetime import datetime
from sqlalchemy import or_

# Create a Blueprint



@app.route("/user/search_parking_lots", methods=['GET'])
def user_search_parking_lots():
    """Search for available parking lots based on name, address or pincode"""
    search_term = request.args.get('q', '')
    
    # Search in multiple fields with partial matching
    parking_lots = ParkingLot.query.filter(
        or_(
            ParkingLot.prime_location_name.ilike(f'%{search_term}%'),
            ParkingLot.address.ilike(f'%{search_term}%'),
            ParkingLot.pincode.ilike(f'%{search_term}%')
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
@app.route("/user/book_spot", methods=['POST'])
def book_parking_spot():
    """Book a parking spot"""
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
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
        # Create reservation with explicit timestamp
        current_time = datetime.utcnow()
        reservation = Reservation(
            spot_id=spot_id,
            user_id=session['user_id'],
            parking_timestamp=current_time,
            status='active'
        )
        
        # Update spot status to occupied
        spot.status = 'O'
        
        # Add and commit in proper order
        db.session.add(reservation)
        db.session.flush()  # This ensures the reservation gets an ID
        db.session.commit()
        
        print(f"DEBUG: Created reservation ID {reservation.id} with timestamp {reservation.parking_timestamp}")
        
        return jsonify({
            'message': 'Parking spot booked successfully',
            'reservation_id': reservation.id,
            'spot_number': spot.spot_number,
            'lot_name': lot.prime_location_name,
            'price_per_hour': lot.price_per_hour,
            'parking_timestamp': reservation.parking_timestamp.isoformat()
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
        current_time = datetime.utcnow()
        duration_seconds = (current_time - reservation.parking_timestamp).total_seconds()
        duration_hours = duration_seconds / 3600
        parking_cost = duration_hours * lot.price_per_hour
        
        # Update reservation with explicit values
        reservation.leaving_timestamp = current_time
        reservation.parking_cost = round(parking_cost, 2)
        reservation.status = 'completed'
        
        # Update spot status to available
        spot.status = 'A'
        
        # Commit changes
        db.session.commit()
        
        print(f"DEBUG: Updated reservation ID {reservation.id}")
        print(f"DEBUG: Parking timestamp: {reservation.parking_timestamp}")
        print(f"DEBUG: Leaving timestamp: {reservation.leaving_timestamp}")
        print(f"DEBUG: Duration: {duration_hours} hours")
        print(f"DEBUG: Cost: ${parking_cost}")
        
        return jsonify({
            'message': 'Parking spot released successfully',
            'reservation_id': reservation.id,
            'duration_hours': round(duration_hours, 2),
            'cost': round(parking_cost, 2),
            'parking_timestamp': reservation.parking_timestamp.isoformat(),
            'leaving_timestamp': reservation.leaving_timestamp.isoformat()
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
        current_time = datetime.utcnow()
        duration_seconds = (current_time - reservation.parking_timestamp).total_seconds()
        duration_hours = duration_seconds / 3600
        current_cost = duration_hours * lot.price_per_hour
        
        result = {
            'active_reservation': True,
            'reservation_id': reservation.id,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'parking_timestamp': reservation.parking_timestamp.isoformat(),
            'duration_hours': round(duration_hours, 2),
            'current_cost': round(current_cost, 2),
            'price_per_hour': lot.price_per_hour
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
            'parking_timestamp': reservation.parking_timestamp.isoformat(),
            'leaving_timestamp': reservation.leaving_timestamp.isoformat() if reservation.leaving_timestamp else None,
            'status': reservation.status,
            'parking_cost': reservation.parking_cost,
            'price_per_hour': lot.price_per_hour
        })
    
    return jsonify(result)

# Route for the user dashboard page
