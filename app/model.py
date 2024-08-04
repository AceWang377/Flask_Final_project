from flask_login import UserMixin
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer


from app import db, login_manager, app
from datetime import datetime

# Association table for game members 使用前定义user and hoopgame的关系
game_members = db.Table('game_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.user_id'), primary_key=True),
    db.Column('game_id', db.Integer, db.ForeignKey('hoops.game_id'), primary_key=True)
)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True, index=True)
    password = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(64), nullable=False, unique=True, index=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    profile_image = db.Column(db.String(128), nullable=True, default='default.jpg')
    games = db.relationship('HoopgameModel', secondary=game_members, backref=db.backref('players', lazy='dynamic'))

    def __repr__(self):
        return f"User '{self.username}', '{self.user_id}'"

    def get_id(self):
        return str(self.user_id)  # Flask-Login 要求返回字符串类型的 ID

    def get_token(self, expires_sec=300):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'user_id': self.user_id}, salt='token-generator')


    @staticmethod
    def verify_token(token):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = serializer.loads(token, salt='token-generator', max_age=300)['user_id']
        except:
            return None
        return User.query.get(user_id)

    @staticmethod
    def verify_reset_token(token):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = serializer.loads(token, salt='token-generator', max_age=300)['user_id']
        except:
            return None
        return User.query.get(user_id)




class VideosModel(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False, unique=True, index=True)
    path = db.Column(db.String(200), nullable=False)


class LocationModel(db.Model):
    __tablename__ = 'locations'
    locals_id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address_name = db.Column(db.String(300), nullable=False)

    def __repr__(self):
        return f"Location{self.locals_id}, {self.address_name}, {self.latitude}, {self.longitude}"


class HoopgameModel(db.Model):
    __tablename__ = 'hoops'
    game_id = db.Column(db.Integer, primary_key=True)
    game_location_id = db.Column(db.Integer, db.ForeignKey('locations.locals_id'))
    location = db.relationship('LocationModel', backref=db.backref('hoopgames', lazy='dynamic'))
    game_name = db.Column(db.String(300), nullable=False)
    game_date = db.Column(db.DateTime, nullable=False)
    game_duration = db.Column(db.Integer, nullable=False)
    game_description = db.Column(db.String(300), nullable=False)
    game_cost = db.Column(db.Float, nullable=False)
    game_players_number = db.Column(db.Integer, nullable=False)
    chat_room = db.relationship('ChatRoomModel', back_populates='game', uselist=False, lazy='joined')

    def __repr__(self):
        return f"Hoopgame{self.game_id}, {self.game_name}, {self.game_date}, {self.game_location}"

class ChatRoomModel(db.Model):
    __tablename__ = 'chatrooms'
    id = db.Column(db.Integer, primary_key=True)
    chat_room_name = db.Column(db.String(255), nullable=False, unique=True)  # 添加聊天室名称字段
    game_id = db.Column(db.Integer, db.ForeignKey('hoops.game_id'), nullable=False)
    game = db.relationship('HoopgameModel', back_populates='chat_room')
    messages = db.relationship('MessageModel', back_populates='chat_room', lazy='dynamic')

    def __repr__(self):
        return f"<ChatRoom {self.id} associated with game {self.game_id}>"

class MessageModel(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_room_id = db.Column(db.Integer, db.ForeignKey('chatrooms.id'), nullable=False)
    chat_room = db.relationship('ChatRoomModel', back_populates='messages')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    user = db.relationship('User', backref='messages')  # 添加这行来引用 User 模型
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return f"<Message {self.id} by user {self.user_id}>"


class CommentModel(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    email = db.Column(db.String(255), nullable=False, index=True)  # Adjusted length and removed unique constraint
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Comment {self.id} by {self.name}, email {self.email}>"


