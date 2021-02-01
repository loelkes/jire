from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateTimeLocalField, SelectField
import wtforms.validators as validators
import pytz


class ReservationForm(FlaskForm):

    start_time = DateTimeLocalField(label='Day and time',
                                    validators=[validators.InputRequired()],
                                    format='%Y-%m-%dT%H:%M')

    timezone = SelectField(label='Timezone',
                           choices=[(tz, tz.replace('_', ' ')) for tz in pytz.common_timezones],
                           default='Europe/Berlin')

    _name_validators = [
        validators.InputRequired(),
        validators.Regexp('^[a-zA-Z0-9_ -]*$',
                          message='Allowed for room names are: a-z, 0-9, -, _ and space.')
    ]
    name = StringField(label='Room name', validators=_name_validators)

    submit = SubmitField(label='Submit')
