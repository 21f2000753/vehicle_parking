from flask import current_app as app, jsonify, request, render_template, redirect, url_for, session, flash
from backend.models import db, User

@app.route('/')
def home():
    return render_template('welcome.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(
            username=data['username'], 
            email=data['email']
        ).first()
        if user:
            return jsonify({'message': 'User already exists'})
        else:
            user = User(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                role='user',
                address=data['address'],
                pincode=data['pincode']
            )
            db.session.add(user)
            db.session.commit()
            return jsonify({'message': 'User registered successfully'})
    
    return render_template('register.html')
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.form
    user = User.query.filter_by(username=data['username']).first()
    
    if user and data['password'] == user.password:
        session['user_id'] = user.id
        session['username'] = user.username
        
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    else:
        error = "Invalid username or password"
        return render_template('login.html', error=error)
    

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('login'))
    
    return render_template('admin_dashboard.html', username=session['username'])

@app.route("/user_dashboard")
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))        
    return render_template("user_dashboard.html")

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))