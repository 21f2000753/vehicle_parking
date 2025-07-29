from flask import current_app as app, jsonify, request, render_template, redirect, url_for
from backend.models import db, User, ParkingLot, ParkingSpot, Reservation

@app.route("/create_parking_lot", methods=["POST"])
def create_parking_lot():
    data = request.form
    
    new_lot = ParkingLot(
        prime_location_name=data["prime_location_name"],
        price_per_hour=float(data["price_per_hour"]),
        address=data["address"],
        pincode=data["pincode"],
        maximum_number_of_spots=int(data["maximum_number_of_spots"])
    )
    
    db.session.add(new_lot)
    db.session.commit()
    
    for i in range(1, int(data["maximum_number_of_spots"]) + 1):
        spot = ParkingSpot(
            lot_id=new_lot.id,
            spot_number=str(i),
            status="A"  # Available
        )
        db.session.add(spot)
    
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route('/all_parking_lots', methods=['GET'])
def get_all_parking_lots():
    parking_lots = ParkingLot.query.all()
    result = []

    for lot in parking_lots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        spot_data = []
        occupied_count = 0

        for spot in spots:
            occupied = spot.status == 'O'
            if occupied:
                occupied_count += 1
            spot_data.append({
                'spot_number': spot.spot_number,
                'status': spot.status
            })

        result.append({
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pincode': lot.pincode,
            'price_per_hour': lot.price_per_hour,
            'max_spots': lot.maximum_number_of_spots,
            'occupied': occupied_count,
            'spots': spot_data
        })

    return jsonify(result)

@app.route('/edit_parking_lot', methods=['GET', 'POST'])
def edit_parking_lot():
    if request.method == 'POST':
        data = request.form
        lot_id = data.get('id')
        
        parking_lot = ParkingLot.query.get(lot_id)
        
        if parking_lot:
            parking_lot.prime_location_name = data['name']
            parking_lot.address = data['address']
            parking_lot.pincode = data['pincode']
            parking_lot.price_per_hour = float(data['price_per_hour'])
            old_max_spots = parking_lot.maximum_number_of_spots
            new_max_spots = int(data['maximum_number_of_spots'])
            parking_lot.maximum_number_of_spots = new_max_spots
            
            db.session.commit()
            
            existing_spots = ParkingSpot.query.filter_by(lot_id=parking_lot.id).all()
            current_spot_count = len(existing_spots)
            
            if new_max_spots > current_spot_count:
                for i in range(current_spot_count + 1, new_max_spots + 1):
                    spot = ParkingSpot(
                        lot_id=parking_lot.id,
                        spot_number=str(i),
                        status="A"
                    )
                    db.session.add(spot)
                db.session.commit()
            # If spot count decreased, handle carefully
            elif new_max_spots < current_spot_count:
                # Get spots to remove, starting from highest number
                spots_to_remove = sorted(
                    existing_spots, 
                    key=lambda x: int(x.spot_number), 
                    reverse=True
                )[:current_spot_count - new_max_spots]
                
                for spot in spots_to_remove:
                    # Check if spot is not occupied before removing
                    if spot.status != 'O':
                        # Check for associated reservations
                        has_reservations = Reservation.query.filter_by(spot_id=spot.id).first() is not None
                        if not has_reservations:
                            db.session.delete(spot)
                    else:
                        # For occupied spots, we could handle differently
                        # For now, just leave them but maybe mark as unavailable in the future
                        pass
                
                db.session.commit()
            
            return redirect(url_for("admin_dashboard"))
        else:
            return jsonify({'error': 'Parking lot not found'}), 404
    
    # If GET request, render the edit form
    return render_template('edit_parking_lot.html')

@app.route('/delete_parking_lot', methods=['GET', 'POST'])
def delete_parking_lot():
    if request.method == 'POST':
        data = request.form
        parking_lot = ParkingLot.query.filter_by(
            prime_location_name=data['name']
        ).first()
        
        if parking_lot:
            # Check if any spots in this lot are occupied
            occupied_spots = ParkingSpot.query.filter_by(
                lot_id=parking_lot.id, 
                status='O'
            ).count()
            
            if occupied_spots > 0:
                flash(f'Cannot delete parking lot "{parking_lot.prime_location_name}". {occupied_spots} spots are currently occupied.', 'error')
                return redirect(url_for('admin_dashboard'))
            
            # First delete all associated spots (only if all are empty)
            ParkingSpot.query.filter_by(lot_id=parking_lot.id).delete()
            
            # Then delete the parking lot
            db.session.delete(parking_lot)
            db.session.commit()
            
            flash(f'Parking lot "{parking_lot.prime_location_name}" has been successfully deleted.', 'success')
            return redirect(url_for("admin_dashboard"))
        else:
            return jsonify({'error': 'Parking lot not found'}), 404
    
    # If GET request, render the delete confirmation page
    return render_template('delete_parking_lot.html')

@app.route('/create_parking_spot', methods=['GET', 'POST'])
def create_parking_spot():
    if request.method == 'POST':
        data = request.form
        parking_spot = ParkingSpot(
            spot_number=data['spot_number'],
            lot_id=data['lot_id'],
            status="A"  # Available
        )
        db.session.add(parking_spot)
        db.session.commit()
        return jsonify({'message': 'Parking spot created successfully'})
    
    # If GET request, render the registration form
    return render_template('create_parking_spot.html')

@app.route('/edit_parking_spot', methods=['GET', 'POST'])
def edit_parking_spot():
    if request.method == 'POST':
        data = request.form
        spot_id = data.get('id')
        
        parking_spot = ParkingSpot.query.get(spot_id)
        if parking_spot:
            parking_spot.spot_number = data['spot_number']
            parking_spot.status = data['status']
            db.session.commit()
            return jsonify({'message': 'Parking spot edited successfully'})
        else:
            return jsonify({'message': 'Parking spot not found'})
    
    # If GET request, render the form
    return render_template('edit_parking_spot.html')

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    result = []
    
    for user in users:
        result.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'address': user.address,
            'pincode': user.pincode
        })
    
    return jsonify(result)

@app.route('/active_bookings', methods=['GET'])
def get_active_bookings():
    """Get all active reservations/bookings with detailed information"""
    # Query all active reservations
    active_reservations = Reservation.query.filter_by(status='active').all()
    result = []
    
    for reservation in active_reservations:
        # Get associated spot information
        spot = ParkingSpot.query.get(reservation.spot_id)
        if not spot:
            continue
            
        # Get lot information
        lot = ParkingLot.query.get(spot.lot_id)
        if not lot:
            continue
            
        # Get user information
        user = User.query.get(reservation.user_id)
        if not user:
            continue
            
        result.append({
            'id': reservation.id,
            'user_id': user.id,
            'username': user.username,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'start_time': reservation.parking_timestamp.isoformat() if reservation.parking_timestamp else None,
            'end_time': reservation.leaving_timestamp.isoformat() if reservation.leaving_timestamp else None,
            'total_cost': reservation.parking_cost if reservation.parking_cost else None,
            'status': reservation.status
        })
    
    return jsonify(result)

@app.route('/all_parking_spots', methods=['GET'])
def get_all_parking_spots():
    """Get all parking spots with lot information"""
    parking_spots = ParkingSpot.query.all()
    result = []
    
    for spot in parking_spots:
        # Get lot information
        lot = ParkingLot.query.get(spot.lot_id)
        if not lot:
            continue
            
        result.append({
            'id': spot.id,
            'spot_number': spot.spot_number,
            'status': spot.status,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name
        })
    
    return jsonify(result)

@app.route('/parking_spots', methods=['GET'])
def get_lot_parking_spots():
    """Get parking spots for a specific lot"""
    lot_id = request.args.get('lot_id')
    if not lot_id:
        return jsonify({'error': 'Lot ID is required'}), 400
        
    # Get lot information first
    lot = ParkingLot.query.get(lot_id)
    if not lot:
        return jsonify({'error': 'Parking lot not found'}), 404
        
    # Get all spots for this lot
    parking_spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    result = []
    
    for spot in parking_spots:
        result.append({
            'id': spot.id,
            'spot_number': spot.spot_number,
            'status': spot.status,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name
        })
    
    return jsonify(result)

# Fix for the delete_parking_spot route to handle DELETE requests
@app.route('/delete_parking_spot', methods=['GET', 'POST', 'DELETE'])
def delete_parking_spot():
    if request.method in ['POST', 'DELETE']:
        # For POST, get data from form
        if request.method == 'POST':
            data = request.form
            spot_id = data.get('id')
        # For DELETE, get data from query parameters
        else:  # DELETE
            spot_id = request.args.get('id')
        
        if not spot_id:
            return jsonify({'error': 'Spot ID is required'}), 400
            
        parking_spot = ParkingSpot.query.get(spot_id)
        if parking_spot:
            # Check if spot is available before deleting
            if parking_spot.status == 'O':
                return jsonify({'error': 'Cannot delete occupied parking spot'}), 400
                
            db.session.delete(parking_spot)
            db.session.commit()
            return jsonify({'message': 'Parking spot deleted successfully'})
        else:
            return jsonify({'error': 'Parking spot not found'}), 404
    
    # If GET request, render the form
    return render_template('delete_parking_spot.html')


@app.route('/search_parking_lots', methods=['GET'])
def search_parking_lots():
    """Search parking lots by name, address or pincode"""
    search_term = request.args.get('q', '')
    if not search_term:
        return jsonify([])
    
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
        
        result.append({
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pincode': lot.pincode, 
            'price_per_hour': lot.price_per_hour,
            'max_spots': lot.maximum_number_of_spots,
            'occupied': occupied_count,
            'available': lot.maximum_number_of_spots - occupied_count
        })
    
    return jsonify(result)

@app.route('/search_users', methods=['GET'])
def search_users():
    """Search users by username, email, or address"""
    search_term = request.args.get('q', '')
    if not search_term:
        return jsonify([])
    
    # Search in multiple fields with partial matching
    users = User.query.filter(
        or_(
            User.username.ilike(f'%{search_term}%'),
            User.email.ilike(f'%{search_term}%'),
            User.address.ilike(f'%{search_term}%'),
            User.pincode.ilike(f'%{search_term}%')
        )
    ).all()
    
    result = []
    for user in users:
        result.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'address': user.address,
            'pincode': user.pincode
        })
    
    return jsonify(result)

@app.route('/search_reservations', methods=['GET'])
def search_reservations():
    """Search reservations by user, date, or status"""
    search_term = request.args.get('q', '')
    status_filter = request.args.get('status', '')  # active, completed, cancelled
    
    # Start with a base query
    query = Reservation.query
    
    # Add status filter if provided
    if status_filter:
        query = query.filter(Reservation.status == status_filter)
    
    # Add search term if provided
    if search_term:
        # We need to join with User to search by username
        reservations = query.join(User).filter(
            or_(
                User.username.ilike(f'%{search_term}%'),
                User.email.ilike(f'%{search_term}%')
                # Add other fields to search on as needed
            )
        ).all()
    else:
        # If no search term, return all reservations with the status filter
        reservations = query.all()
    
    result = []
    for reservation in reservations:
        # Get user information
        user = User.query.get(reservation.user_id)
        if not user:
            continue
            
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
            'user_id': user.id,
            'username': user.username,
            'user_email': user.email,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'start_time': reservation.start_time.isoformat() if reservation.start_time else None,
            'end_time': reservation.end_time.isoformat() if reservation.end_time else None,
            'status': reservation.status,
            'total_cost': reservation.total_cost
        })
    
    return jsonify(result)

@app.route('/reservations', methods=['GET'])
def get_all_reservations():
    """Get all reservations with optional status filter"""
    status_filter = request.args.get('status', '')
    
    query = Reservation.query
    if status_filter:
        query = query.filter(Reservation.status == status_filter)
    
    reservations = query.all()
    result = []
    
    for reservation in reservations:
        # Get user information
        user = User.query.get(reservation.user_id)
        if not user:
            continue
            
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
            'user_id': user.id,
            'username': user.username,
            'user_email': user.email,
            'spot_id': spot.id,
            'spot_number': spot.spot_number,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'start_time': reservation.start_time.isoformat() if reservation.start_time else None,
            'end_time': reservation.end_time.isoformat() if reservation.end_time else None,
            'status': reservation.status,
            'total_cost': reservation.total_cost
        })
    
    return jsonify(result)