from flask_wtf import FlaskForm
from wtforms import StringField,FloatField, PasswordField, SubmitField, EmailField, DateField, TelField, TextAreaField, DecimalField, RadioField, DateTimeLocalField

from wtforms.fields.choices import SelectField
from wtforms.fields.datetime import DateTimeField
from wtforms.fields.numeric import IntegerField
from wtforms.fields.simple import BooleanField
from wtforms.validators import DataRequired, Length, Regexp, EqualTo, NumberRange, ValidationError, Email
from datetime import date
from flask_wtf.file import FileField, FileAllowed

class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(),
                    Regexp(r'^\w+$', message='Username must contain only letters, numbers, or underscores')
])
    password = PasswordField('Password', validators=[DataRequired(),
                    Regexp(r'^(?=.*[a-zA-Z])(?=.*[0-9])(?=.*[\W_]).{8,}$',
           message='Password must be at least 8 characters long and include letters, numbers, and special characters')
])

    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='The two password fields did not match')])

    email_address = EmailField('Email Address', validators=[DataRequired(),
                    Regexp(r'^\S+@\S+\.\S+$', message='Invalid email address') # validate email address
])
    date_of_birthday = DateField('Date of Birthday',validators=[DataRequired()])
    tel_phone = TelField('Telphone', validators=[DataRequired(),
                    Regexp(r'^\+?1?\d{9,15}$', message="Invalid phone number format.")
])
    location_address = TextAreaField('Address', validators=[DataRequired()])
    height = DecimalField('Height(cm)', validators=[DataRequired(), NumberRange(min=140,max=211,message='Field must be between 140cm and 211cm')])
    weight = DecimalField('Weight(kg)', validators=[DataRequired(), NumberRange(min=40,max=300,message='Field must be between 3kg and 300kg')])
    submit = SubmitField('Sign Up')
    # 如果写成validate_加上form名称就会被自动调用执行
    def validate_date_of_birthday(form, field):
        if field.data > date.today():
            raise ValidationError('Date cannot be greater than today')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password',validators=[DataRequired()])
    remember_me = BooleanField('Remember Me', default=False)
    submit = SubmitField('Login')

class RequiredResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Verified Email')

class ResetPasswordForm(FlaskForm):
    current_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo("current_password", message='Passwords must match')])
    submit = SubmitField('Reset')

# upload video file
class UploadFileForm(FlaskForm):
    video_filename = StringField('Video Filename', validators=[DataRequired()])
    folder_selection = RadioField('Folder Selection', choices=[('ace_basketball_life','Ace Highlight'),('english_learning','English Learning'),('training_tutorial','Training Tutorial'),('love_story','Love Story')],validators=[DataRequired()])
    video_file = FileField('Video File', validators=[DataRequired(), FileAllowed(['mp4', 'avi', 'mov', 'flv', 'mkv'])])
    submit = SubmitField('Upload')


class CreateGameForm(FlaskForm):
    event_name = StringField('Event Name', validators=[DataRequired()])
    date_time = DateTimeLocalField('Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    duration = DecimalField('Duration (hours)', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[DataRequired()])
    longitude = FloatField('Longitude', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    cost = StringField('Cost(£/p)', validators=[DataRequired()])
    maximum_number_of_players = IntegerField('Maximum Number of Players', validators=[DataRequired()])
    submit = SubmitField('Create Game')

# upload user profile
class UpdateProfileForm(FlaskForm):
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')


class LeaveMessageForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    message = StringField('Message', validators=[DataRequired()])
    submit = SubmitField('Submit')
