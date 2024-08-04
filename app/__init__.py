import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_mailman import Mail
from flask_migrate import Migrate
from flask_socketio import SocketIO, join_room, send
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__) # create flask app
app.config['SECRET_KEY'] = b'WR#&f&+%78er0we=%799eww+#7^90-;s' # keep secret with flask sessions


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



# Password encode 密码加密
bcrypt = Bcrypt(app)


# email confirm
app.config['MAIL_SERVER'] = 'stmp.fastmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'hooplife377@fastmail.com'
app.config['MAIL_PASSWORD'] = '2h3a3b2x944j3u8j'
#
# # initialize mail
mail = Mail(app)


# login manage
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login_page'

basedir = os.path.abspath(os.path.dirname(__file__)) # get the path of current file
# 设置 SQL 数据库的 URI，数据库文件位于项目目录下的 data 文件夹中，文件名为 hooplife
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:aqj710310@localhost/hooplife'
# 禁用 SQLAlchemy 的修改追踪，以减少额外的内存开销。
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# initialize sql in flask
db = SQLAlchemy(app)
migrate = Migrate(app, db)




# upload avatar
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # limit to 16MB


from app import views
from app.model import *

# 注册一个shell上下文处理器 便于频繁地在 Flask shell 中与数据库进行交互
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User,VideosModel=VideosModel,datetime=datetime, LocationModel=LocationModel,
                HooplifeModel=HoopgameModel, MessageModel=MessageModel, ChatRoomModel=ChatRoomModel,
                CommentModel=CommentModel)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))





