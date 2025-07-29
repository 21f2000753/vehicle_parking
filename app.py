from flask import Flask
from backend.models import db

app = Flask(__name__)

def setup_app():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vehicle_parking.sqlite3"  # Having db file
    app.secret_key = 'Dev@1234576'
    db.init_app(app)  
    app.app_context().push()
    db.create_all()
    app.debug = True
    

setup_app()



import backend.create_initial_data
import backend.routes
import backend.admin
import backend.customer

if __name__ == "__main__":
    app.run()
