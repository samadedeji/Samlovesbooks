import os

from app import create_app
from app.models import db

config_object = "config.ProdConfig" if os.environ.get("FLASK_ENV") == "production" else "config.DevConfig"
app = create_app(config_object)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
