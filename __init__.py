from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes import main
    from .admin_routes import admin
    from .user_routes import user

    app.register_blueprint(main)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(user, url_prefix='/user')

    with app.app_context():
        db.create_all()

        # Auto-create admin user
        from werkzeug.security import generate_password_hash
        if not User.query.filter_by(username='Harshad_12').first():
            # Create admin user
            admin_user = User(
                username='Harshad_12',
                password=generate_password_hash('Harsh@1207'),
                is_admin=True,
                balance=100.0
            )
            db.session.add(admin_user)
            db.session.commit()            

    return app
