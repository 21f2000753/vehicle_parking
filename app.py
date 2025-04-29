# Starting of the app
from flask import Flask
from backend.models import db
# from backend.routes import api

app = Flask(__name__)  # <-- move creation here at the top

def setup_app():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vechicle_parking.sqlite3"  # Having db file
    db.init_app(app)  # Flask app connected to db(SQLAlchemy)
    app.app_context().push()  # Direct access to other modules
    db.create_all()
    app.debug = True
    print("Vehicle Parking app is started...")

# Call the setup
setup_app()

@app.route('/')
def home():
    return "Welcome to the Vehicle Parking App!"


if __name__ == "__main__":
    app.run()
