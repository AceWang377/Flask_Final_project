import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_mailman import Mail
from flask_migrate import Migrate
from flask_socketio import SocketIO, join_room, send
from flask_sqlalchemy import SQLAlchemy
# from flask_wtf.csrf import CSRFProtect
# from flask_wtf.csrf import generate_csrf

app = Flask(__name__) # create flask app
app.config['SECRET_KEY'] = b'****' # keep secret with flask sessions
# Configure CSRF Protectio
# csrf = CSRFProtect(app)

# socketio
socketio = SocketIO(app)
@socketio.on('connect')
def on_connect():
    print('User connected!')


@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return False  # Prevent unauthenticated message sending
    message = MessageModel(content=data['message'], user_id=current_user.id, game_id=data['game_id'])
    db.session.add(message)
    db.session.commit()
    send({'msg': data['message'], 'username': current_user.username, 'game_id': data['game_id']}, room=data['game_id'])


@socketio.on('join')
def on_join(data):
    join_room(data['game_id'])



# Password encode
bcrypt = Bcrypt(app)


# email confirm
app.config['MAIL_SERVER'] = 'smtp.fastmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'hooplife377@fastmail.com'
app.config['MAIL_PASSWORD'] = '****'
#
# # initialize mail
mail = Mail(app)


# login manage
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login_page'

basedir = os.path.abspath(os.path.dirname(__file__)) # get the path of current file
# Set the URI of the SQL database. The database file is located in the data folder under the project directory and the file name is hooplife
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:******@localhost/hooplife'

from sqlalchemy.dialects.postgresql.base import PGDialect
PGDialect._get_server_version_info = lambda *args: (9, 2)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://zixuan:uXwqAMRtJkmngBVlxFvKmA@hooplife-15923.8nj.gcp-europe-west1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full'
# export DATABASE_URL=""


# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ueab1i7cjhbhng:p43658d39f9b45b652101bf45d3972e91782ff379c76c8288942c5de827ae4375@ce0lkuo944ch99.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/df2e9qtqtosjel'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ueab1i7cjhbhng:p43658d39f9b45b652101bf45d3972e91782ff379c76c8288942c5de827ae4375@ce0lkuo944ch99.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/df2e9qtqtosjel?sslmode=require'

# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://ueab1i7cjhbhng:p43658d39f9b45b652101bf45d3972e91782ff379c76c8288942c5de827ae4375@ce0lkuo944ch99.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/df2e9qtqtosjel'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# initialize sql in flask
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# upload avatar
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # limit to 16MB


from app import views
from app.model import *

# Register a shell context processor to facilitate frequent interaction with the database in the Flask shell
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User,datetime=datetime, LocationModel=LocationModel,
                HooplifeModel=HoopgameModel, MessageModel=MessageModel, ChatRoomModel=ChatRoomModel,
                CommentModel=CommentModel)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# @app.context_processor
# def inject_csrf_token():
#     return dict(csrf_token=generate_csrf())

# @app.context_processor
# def context_processor():
#     return {'csrf_token': generate_csrf()}  # This would cause the error you see.



