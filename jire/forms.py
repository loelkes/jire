from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateTimeLocalField, SelectField
import wtforms.validators as formValidators
import pytz


class ReservationForm(FlaskForm):

    start_time = DateTimeLocalField(label='Day and time',
                                    validators=[formValidators.InputRequired()],
                                    format='%Y-%m-%dT%H:%M')

    timezone = SelectField(label='Timezone',
                           choices=[(tz, tz.replace('_', ' ')) for tz in pytz.common_timezones],
                           default='Europe/Berlin')

    name = StringField(label='Room name',
                       validators=[formValidators.InputRequired()])

    submit = SubmitField(label='Submit')
