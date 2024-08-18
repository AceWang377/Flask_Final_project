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
from app.model import User, LocationModel, HoopgameModel, MessageModel, ChatRoomModel, CommentModel
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
            current_app.logger.error(f'Something went wrong {e}')
            print('Something went wrong:', e)
            return False
        return True



# forget password
@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    form = RequiredResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if send_mail(user):
                flash('A reset link has been sent to your email. Please check your email.', 'success')
            else:
                flash('Failed to send email, please try again later.', 'danger')
            return redirect(url_for('login_page'))
        else:
            flash('No account found with that email.', 'danger')
    return render_template('forget_password.html',form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if 'reset_successful' in session:
        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('login_page'))

    if user is None and request.method == 'GET':
        flash('Invalid or expired token, please try again.','warning')
        return redirect(url_for('forget_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.current_password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        session['reset_successful'] = True
        return redirect(url_for('reset_password', token=token))

    return render_template('reset_password.html',form=form, token=token)




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
        location_name = form.location.data
        longitude = form.longitude.data
        latitude = form.latitude.data
        description = form.description.data
        players_num = form.maximum_number_of_players.data
        cost = form.cost.data

        if date_time < datetime.now():
            flash('Cannot create a game in the past.', 'danger')
            return redirect(url_for('activity_page'))


        # Find or create a location
        location = LocationModel.query.filter_by(latitude=latitude, longitude=longitude).first()
        if not location:
            new_location = LocationModel(latitude=latitude, longitude=longitude, address_name=location_name)
            db.session.add(new_location)
            db.session.flush()  # Need to generate ID immediately
        else:
            flash('There is a game with that location', 'danger')
            return redirect(url_for('activity_page'))

        # Create new game
        new_game = HoopgameModel(game_name=event_name, game_date=date_time, game_duration=duration,
                                 game_description=description,
                                 game_location_id=new_location.locals_id, game_cost=cost,
                                 game_players_number=players_num)
        db.session.add(new_game)

        # Try to create chat rooms simultaneously
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

'''
# Use the Nominatim API to convert addresses to latitude and longitude
def geocode_address(address):
    try:
        # Sending a request to the Nominatim API
        response = requests.get(f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={address}")

        # Check HTTP status code
        if response.status_code != 200:
            print(f"Failed to get data: HTTP status code {response.status_code}")
            return None, None

        # Check if the returned content is in JSON format
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()  # Try to parse JSON
            if data and isinstance(data, list) and len(data) > 0 and 'lat' in data[0] and 'lon' in data[0]:
                lat = data[0]['lat']
                lon = data[0]['lon']
                print(f"Geocoded {address} to {lat}, {lon}")  # Print or record longitude and latitude
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
'''

# get-locations
@app.route('/get-locations')
def get_locations():
    current_time = datetime.utcnow()
    # LocationModel is associated with HoopgameModel and has a foreign key relationship
    locations = db.session.query(LocationModel, HoopgameModel).join(
        HoopgameModel, LocationModel.hoopgames).filter(HoopgameModel.game_date>current_time).all()
    locations_data = [
        {
            'lat': loc.LocationModel.latitude,
            'lon': loc.LocationModel.longitude,
            'address': loc.LocationModel.address_name,
            'game_id': loc.HoopgameModel.game_id,
            'game_name': loc.HoopgameModel.game_name
        }
        for loc in locations
    ]
    return jsonify(locations_data)


@login_required
@app.route('/game_details/<int:game_id>')
def game_details(game_id):
    game = HoopgameModel.query.get_or_404(game_id)  # Get the game or return 404 error
    return render_template('game_details.html', game=game)


@app.route('/community')
def community():
    return render_template('community_Intro.html')



# chatrooms
rooms = {}  # Store room information and messages

# community
@app.route('/community',defaults={'game_id': None})
@app.route('/community/<int:game_id>', methods=['GET', 'POST'])
@login_required
def community_page(game_id):
    game = HoopgameModel.query.get_or_404(game_id)  # Get game details
    room = game.game_name  # Set room name as game name
    if request.method == "POST":
        input_name = request.form.get("name")
        # Check if the name entered is the same as the currently logged in user name
        if input_name != current_user.username:
            flash('You must enter your own username to join the chat.', 'error')
            return redirect(url_for("community_page", game_id=game_id))
        session['name'] = input_name  # Store username in the session
        session['room'] = room  # Store room name in the session
        # Initialize the room if it does not exist
        if room not in rooms:
            rooms[room] = {"messages": [], "members": 0}
        return redirect(url_for("room", game_id=game_id))
    # For GET requests, displays the community homepage with a non-editable game name
    return render_template("community_home.html", game=game, name=session.get('name', ''))


@app.route("/room/<int:game_id>", methods=['GET'])
@login_required
def room(game_id):
    game = HoopgameModel.query.get_or_404(game_id)  # Get game details
    room_name = game.game_name
    # room = session.get("room")
    # Try getting the room name from the session and make sure it matches the game name
    if 'room' not in session or session['room'] != room_name:
        session['room'] = room_name  # Update the room name in the session
        if room_name not in rooms:
            rooms[room_name] = {"messages": [], "members": 0}  # Initialize the room
    # Get chat room ID
    chat_room = ChatRoomModel.query.filter_by(game_id=game_id).first()
    if not chat_room:
        # If you can't find a chat room, you may need to create one
        flash('Chat room does not exist. Please create a room first.', 'warning')
        return redirect(url_for("community_page", game_id=game_id))
    # Loading historical messages from the database
    messages = MessageModel.query.filter_by(chat_room_id=chat_room.id).order_by(MessageModel.timestamp.asc()).all()

    # Convert message format for front-end display
    history_msgs = [{
        "username": msg.user.username,  # Ensure the correct user information is associated
        "message": msg.content,
        "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')  # Formatting timestamps
    } for msg in messages]

    if room_name != game.game_name:
        # If the room name does not match, redirect to the community page to set it correctly
        flash('Room does not match the selected game.', 'warning')
        return redirect(url_for("community_page", game_id=game_id))

    # Make sure the room exists in the dictionary, otherwise redirect back to the community page
    if room_name not in rooms:
        flash('Room does not exist. Please join again.', 'warning')
        return redirect(url_for("community_page", game_id=game_id))

    # Render the chat room page and pass necessary data
    return render_template("community.html", room=room, game=game, messages=history_msgs)


### SocketIO event handling code
# Handle received messages
@socketio.on("message")
def handle_message(data):
    print("Received data:", data)  # Debug: print received data
    room_name = data["room"]
    username = data["name"]
    message_content = data["message"]
    chat_room = ChatRoomModel.query.filter_by(chat_room_name=room_name).first()
    if not chat_room:
        print("Chat room does not exist:", room_name)  # Debug: Print error information
        emit('error', {'message': 'Chat room does not exist.'}, room=request.sid)  # Send an error to the requesting client
        return  # Proper error handling
    if room_name not in rooms:
        rooms[room_name] = {"messages": [], "members": 0}  # If it does not exist, initialize the room
    # Create a message instance and save it to the database
    new_message = MessageModel(
        chat_room_id=chat_room.id,  # Make sure you have the correct foreign key relationships or references
        user_id=current_user.user_id,  # Flask-Login UserID
        content=message_content)
    db.session.add(new_message)

    try:
        db.session.commit()
        print("Message saved:", new_message)  # Debug: print saved messages
    except Exception as e:
        db.session.rollback()
        print("Error saving message:", str(e))  # Debug: Print wrong msg
        emit('error', {'message': 'Failed to save message.'}, room=request.sid)
        return

    # Constructing message data
    msg = {
        "username": username,
        "message": message_content
    }
    rooms[room_name]["messages"].append(msg)  # Add the message to the room's message list
    send(msg, room=room_name)  # Send a message to all clients in the room


# When a user joins a room
@socketio.on("join")
def on_join(data):
    user_id = current_user.user_id
    room = data['room']
    name = data.get('name', 'Unknown')
    # The user joins the specified room
    join_room(room)
    # Make sure the room exists in the rooms dictionary
    if room not in rooms:
        rooms[room] = {"messages": [], "members": set(), "count": 0}
    send({"username": name, "message": f"{name} has joined {room}"}, room=room)


# When a user leaves a room
@socketio.on("leave")
def on_leave(data):
    room = data['room']
    name = data['name']
    # The user leaves the specified room
    leave_room(room)
    # Broadcast user leaving message
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
    return redirect(url_for('room', game_id=game_id))  # Assume 'room' is the route for the chat room


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




