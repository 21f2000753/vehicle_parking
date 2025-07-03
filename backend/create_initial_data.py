from flask import current_app as app
from backend.models import db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    if not User.query.filter_by(role='admin').first():
        admin_user = User(
            username='admin',
            email='admin@parking.com',
            password='admin123',
            role='admin',
            address='Admin Office',
            pincode='000000'
        )
        db.session.add(admin_user)
        db.session.commit()