# Starting of the app
from flask import Flask
from backend.models import db
# from backend.routes import api

app = Flask(__name__)  # <-- move creation here at the top

def setup_app():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vehicle_parking.sqlite3"  # Having db file
    app.secret_key = 'Dev@1234576'
    db.init_app(app)  # Flask app connected to db(SQLAlchemy)
    app.app_context().push()  # Direct access to other modules
    db.create_all()
    app.debug = True
    

# Call the setup
setup_app()



import backend.create_initial_data
import backend.routes
import backend.admin
import backend.customer

if __name__ == "__main__":
    app.run()
