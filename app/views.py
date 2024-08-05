import smtplib

from flask import render_template,Flask,request,redirect,url_for,flash,session,jsonify,current_app
import requests
from flask_login import login_required,login_user,logout_user, current_user

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask_socketio import SocketIO, join_room, leave_room, send, disconnect, emit
import secrets
from PIL import Image


from app.form import SignUpForm, LoginForm, ResetPasswordForm, RequiredResetForm, CreateGameForm, UpdateProfileForm, LeaveMessageForm
from app import app, db, bcrypt, login_manager, socketio
from app.model import User, VideosModel, LocationModel, HoopgameModel, MessageModel, ChatRoomModel, CommentModel
from datetime import datetime, date
import random
import os


@app.route('/index')
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/learn_more')
def learn_more():
    return render_template('learn_more.html')

@app.route('/signup',methods=['GET','POST'])
def signup():
    signupform = SignUpForm()
    if signupform.validate_on_submit():
        if User.query.filter_by(username=signupform.username.data).first():
            signupform.username.errors.append('This username is already taken. Please choose another one.', 'danger')
            return render_template('signup.html',signupform=signupform)
        if User.query.filter_by(email=signupform.email_address.data).first():
            signupform.email_address.errors.append('This email address is already taken. Please choose another one')
            return render_template('signup.html', signupform=signupform)
        # Passwords are not explicitly stored in the database
        hashed_password = bcrypt.generate_password_hash(signupform.password.data).decode('utf-8')
        new_user = User(username=signupform.username.data,
                           email=signupform.email_address.data,
                           password=hashed_password,
                           date_joined=datetime.now(),
                           date_of_birth=signupform.date_of_birthday.data,
                           telephone=signupform.tel_phone.data,
                           location=signupform.location_address.data,
                           height=signupform.height.data,
                           weight=signupform.weight.data)
        db.session.add(new_user)
        try:
            db.session.commit()
            flash(f'Your account {new_user.username} has been created','success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            app.logger.error('Error occurred while signing up:%s',str(e))
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('signup.html',signupform=signupform)

# login
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    loginform = LoginForm()

    if loginform.validate_on_submit():
        user = User.query.filter_by(username=loginform.username.data).first()

        if user is not None and bcrypt.check_password_hash(user.password, loginform.password.data):
            remember_me = loginform.remember_me.data
            login_user(user,remember=remember_me) #保持login状态 替换session
            flash(f'User {user.username} Logged in successfully','success')
            return redirect(url_for('home'))
        else:
            flash(f'Invalid username or Incorrect password','danger')
            # // write to userID.file -> [time] : Password was incorrect

    return render_template('login.html',loginform=loginform)


def send_mail(user):
    with current_app.app_context():
        token = user.get_token()

        # Email account credentials
        fastmail_user = 'hooplife377@fastmail.com'
        fastmail_password = '2h3a3b2x944j3u8j'

        # print("user email:",user.email)
        # Email details
        sent_from = fastmail_user
        to = [user.email]
        subject = 'Reset Password for HoopLife'
        body = (f'Hey! This email is sent from {sent_from}. \n\n'
                f'To reset your password, please follow the link below: '
                f'Here is the link { url_for("reset_password", token=token, _external=True) }\n\n'
                f'Click the link to reset your password.')

        # Create the email
        email_text = MIMEMultipart()
        email_text['From'] = sent_from
        email_text['To'] = ', '.join(to)
        email_text['Subject'] = subject
        email_text.attach(MIMEText(body, 'plain'))

        try:
            # Connect to the Fastmail SMTP server and send the email
            server = smtplib.SMTP_SSL('smtp.fastmail.com', 465)
            server.ehlo()
            server.login(fastmail_user, fastmail_password)
            server.sendmail(sent_from, to, email_text.as_string())
            server.close()

            print('Email sent successfully!')
        except Exception as e:
            print('Something went wrong:', e)



# forget password
@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    form = RequiredResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_mail(user)
            flash('Request has been reset. Please check your email.','success')
            return redirect(url_for('login_page'))
    return render_template('forget_password.html',form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid email, please try again.','warning')
        return redirect(url_for('forget_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.current_password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated successfully.','success')
        return redirect('login_page')


    return render_template('reset_password.html',form=form)




# logout
@app.route('/logout')
def logout_page():
    logout_user() # 替换session[].pop()
    flash(f'You have been logged out successful!','success')
    return redirect(url_for('home'))


# Searchgamespage
@app.route('/searchgames', methods=['GET','POST'])
def search_games():
    return render_template('searchgames.html')

@login_required
# Activity page
@app.route('/activity', methods=['GET', 'POST'])
def activity_page():
    form = CreateGameForm()
    today_date = date.today().isoformat()
    if form.validate_on_submit():
        event_name = form.event_name.data
        date_time = form.date_time.data
        duration = form.duration.data
        location_name = form.location.data  # 假设这是地址名称
        longitude = form.longitude.data
        latitude = form.latitude.data
        description = form.description.data
        players_num = form.maximum_number_of_players.data
        cost = form.cost.data

        if date_time < datetime.now():
            flash('Cannot create a game in the past.', 'danger')
            return redirect(url_for('activity_page'))


        # 查找或创建位置
        location = LocationModel.query.filter_by(latitude=latitude, longitude=longitude).first()
        if not location:
            new_location = LocationModel(latitude=latitude, longitude=longitude, address_name=location_name)
            db.session.add(new_location)
            db.session.flush()  # 需要立即生成 ID
        else:
            flash('There is a game with that location', 'danger')
            return redirect(url_for('activity_page'))

        # 创建新游戏
        new_game = HoopgameModel(game_name=event_name, game_date=date_time, game_duration=duration,
                                 game_description=description,
                                 game_location_id=new_location.locals_id, game_cost=cost,
                                 game_players_number=players_num)
        db.session.add(new_game)

        # 尝试同时创建聊天室
        new_chat_room = ChatRoomModel(chat_room_name=event_name, game=new_game)
        db.session.add(new_chat_room)

        try:
            db.session.commit()
            flash('Game successfully added', 'success')
            return redirect(url_for('search_games'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred {str(e)}', 'warning')

    return render_template('activity.html', form=form, today_date=today_date)


# 使用 Nominatim API 将地址转换为经纬度
def geocode_address(address):
    try:
        # 发送请求到 Nominatim API
        response = requests.get(f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={address}")

        # 检查 HTTP 状态码
        if response.status_code != 200:
            print(f"Failed to get data: HTTP status code {response.status_code}")
            return None, None

        # 检查返回的内容是否为 JSON 格式
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()  # 尝试解析 JSON
            if data and isinstance(data, list) and len(data) > 0 and 'lat' in data[0] and 'lon' in data[0]:
                lat = data[0]['lat']
                lon = data[0]['lon']
                print(f"Geocoded {address} to {lat}, {lon}")  # 打印或记录经纬度
                return lat, lon
            else:
                print("No valid location data found.")
        else:
            print("Response not in JSON format.")
    except requests.RequestException as e:
        print(f"Request failed: {e}")
    except ValueError as e:
        print(f"Error decoding JSON: {e}")

    return None, None


# get-locations
@app.route('/get-locations')
def get_locations():
    current_time = datetime.utcnow()
    # LocationModel 关联到 HoopgameModel，且有外键关系
    locations = db.session.query(LocationModel, HoopgameModel).join(
        HoopgameModel, LocationModel.hoopgames).filter(HoopgameModel.game_date>current_time).all()
    locations_data = [
        {
            'lat': loc.LocationModel.latitude,
            'lon': loc.LocationModel.longitude,
            'address': loc.LocationModel.address_name,
            'game_id': loc.HoopgameModel.game_id,  # 获取游戏ID
            'game_name': loc.HoopgameModel.game_name  # 获取游戏名称
        }
        for loc in locations
    ]
    return jsonify(locations_data)


@login_required
@app.route('/game_details/<int:game_id>')
def game_details(game_id):
    game = HoopgameModel.query.get_or_404(game_id)  # 获取游戏或返回404错误
    return render_template('game_details.html', game=game)


@app.route('/community')
def community():
    return render_template('community_Intro.html')



# chatrooms
rooms = {}  # 存储房间信息和消息

# community
@app.route('/community',defaults={'game_id': None})
@app.route('/community/<int:game_id>', methods=['GET', 'POST'])
@login_required
def community_page(game_id):
    game = HoopgameModel.query.get_or_404(game_id)  # 获取游戏详情
    room = game.game_name  # 设置房间名为游戏名称


    if request.method == "POST":
        input_name = request.form.get("name")

        # 检查输入的名字是否与当前登录的用户名一致
        if input_name != current_user.username:
            flash('You must enter your own username to join the chat.', 'error')
            return redirect(url_for("community_page", game_id=game_id))

        session['name'] = input_name  # 存储用户名到会话中
        session['room'] = room  # 存储房间名到会话中

        # 初始化房间如果它不存在
        if room not in rooms:
            rooms[room] = {"messages": [], "members": 0}

        return redirect(url_for("room", game_id=game_id))

    # 对于GET请求，显示社区主页，带有不可编辑的游戏名
    return render_template("community_home.html", game=game, name=session.get('name', ''))


@app.route("/room/<int:game_id>", methods=['GET'])
@login_required
def room(game_id):

    game = HoopgameModel.query.get_or_404(game_id)  # 获取游戏详情
    room_name = game.game_name
    # room = session.get("room")

    # 尝试从会话获取房间名，确保其与游戏名一致
    if 'room' not in session or session['room'] != room_name:
        session['room'] = room_name  # 更新会话中的房间名
        if room_name not in rooms:
            rooms[room_name] = {"messages": [], "members": 0}  # 初始化房间

    # 获取聊天室ID
    chat_room = ChatRoomModel.query.filter_by(game_id=game_id).first()
    if not chat_room:
        # 如果没有找到聊天室，可能需要创建一个
        flash('Chat room does not exist. Please create a room first.', 'warning')
        return redirect(url_for("community_page", game_id=game_id))

    # 从数据库加载历史消息
    messages = MessageModel.query.filter_by(chat_room_id=chat_room.id).order_by(MessageModel.timestamp.asc()).all()

    # 转换消息格式以便前端显示
    history_msgs = [{
        "username": msg.user.username,  # 确保关联正确的用户信息
        "message": msg.content,
        "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')  # 格式化时间戳
    } for msg in messages]

    if room_name != game.game_name:
        # 如果房间名不匹配，重定向到 community 页面进行正确的设置
        flash('Room does not match the selected game.', 'warning')
        return redirect(url_for("community_page", game_id=game_id))

    # 确保房间在字典中存在，否则重定向回 community 页面
    if room_name not in rooms:
        flash('Room does not exist. Please join again.', 'warning')
        return redirect(url_for("community_page", game_id=game_id))

    # 渲染聊天室页面，传递必要的数据
    return render_template("community.html", room=room, game=game, messages=history_msgs)


### SocketIO 事件处理代码
# 处理接收到的消息
@socketio.on("message")
def handle_message(data):
    print("Received data:", data)  # Debug: 打印接收到的数据
    room_name = data["room"]
    username = data["name"]
    message_content = data["message"]

    chat_room = ChatRoomModel.query.filter_by(chat_room_name=room_name).first()
    if not chat_room:
        print("Chat room does not exist:", room_name)  # Debug: 打印错误信息
        emit('error', {'message': 'Chat room does not exist.'}, room=request.sid)  # 发送错误到请求的客户端
        return  # 适当的错误处理

    if room_name not in rooms:
        rooms[room_name] = {"messages": [], "members": 0}  # 如果不存在，则初始化房间

    # 创建消息实例并保存到数据库
    new_message = MessageModel(
        chat_room_id=chat_room.id,  # 确保你有正确的外键关系或引用方式
        user_id=current_user.user_id,  # Flask-Login 用户ID
        content=message_content)
    db.session.add(new_message)

    try:
        db.session.commit()
        print("Message saved:", new_message)  # Debug: 打印保存的消息
    except Exception as e:
        db.session.rollback()
        print("Error saving message:", str(e))  # Debug: 打印错误信息
        emit('error', {'message': 'Failed to save message.'}, room=request.sid)
        return

    # 构建消息数据
    msg = {
        "username": username,
        "message": message_content
    }
    rooms[room_name]["messages"].append(msg)  # 将消息添加到房间的消息列表中
    send(msg, room=room_name)  # 发送消息到房间中的所有客户端


# 当用户加入房间
@socketio.on("join")
def on_join(data):
    user_id = current_user.user_id
    room = data['room']
    name = data.get('name', 'Unknown')
    # 用户加入指定的房间
    join_room(room)

    # 确保房间在 rooms 字典中存在
    if room not in rooms:
        rooms[room] = {"messages": [], "members": set(), "count": 0}


    send({"username": name, "message": f"{name} has joined {room}"}, room=room)


# 当用户离开房间
@socketio.on("leave")
def on_leave(data):
    room = data['room']
    name = data['name']

    # 用户离开指定的房间
    leave_room(room)

    # 广播用户离开消息
    send({"name": name, "message": f"{name} has left the room"}, room=room)


@login_required
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.profile_image = picture_file
            db.session.commit()
            flash('Your account has been updated!', 'success')
            return redirect(url_for('profile'))

    # Set default image if none exists
    image_file = url_for('static', filename='profile_pics/' + current_user.profile_image) if current_user.profile_image else url_for('static', filename='profile_pics/default.jpg')

    game = current_user.games
    # Fetch all chat rooms and messages associated with the current user
    messages = MessageModel.query.filter_by(user_id=current_user.user_id).all()
    chat_rooms = set(message.chat_room for message in messages)

    return render_template("profile.html", user=current_user, game=game, messages=messages, chat_rooms=chat_rooms, image_file=image_file, form=form)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    # Increase the dimensions for better clarity
    output_size = (200, 200)  # Larger dimensions for better image quality

    i = Image.open(form_picture)
    i.thumbnail(output_size)  # Resize the image
    i.save(picture_path)

    return picture_fn


@app.route('/attend-game/<int:game_id>', methods=['POST'])
@login_required
def attend_game(game_id):
    game = HoopgameModel.query.get_or_404(game_id)
    if game not in current_user.games:
        current_user.games.append(game)
        db.session.commit()
        flash('You have successfully joined the game!', 'success')
    else:
        flash('You have already joined this game.', 'info')
    return redirect(url_for('room', game_id=game_id))  # 假设 'room' 是聊天室的路由


@app.route('/check-attendance/<int:game_id>', methods=['GET'])
@login_required
def check_attendance(game_id):
    game = HoopgameModel.query.get(game_id)
    attended = game in current_user.games
    return jsonify({'attended': attended})



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = LeaveMessageForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data
        print(name, email, message)

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Please sign in first.', 'info')
            return redirect(url_for('login_page'))  # Assuming you have a login route

        new_comment = CommentModel(name=name, email=email, content=message, timestamp=datetime.now())
        try:
            db.session.add(new_comment)
            db.session.commit()
            flash('Your message has been sent successfully.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('Error processing your request.', 'error')
            print(e)  # Output the error to your log or console

    return render_template('contact.html', form=form)



@app.route('/comment_board', methods=['GET', 'POST'])
@login_required
def comment_board():
    comments = CommentModel.query.all()
    return render_template('comment_board.html', comments=comments)


# login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# highlight current page
@app.template_filter('is_active')
def is_active(path):
    return 'active' if request.path == path else ''


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error/500.html'), 500




