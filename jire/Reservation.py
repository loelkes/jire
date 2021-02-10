from datetime import datetime, timedelta
from dateutil import parser as dp
from typing import Union
import os
import pytz
from .CustomExceptions import ConferenceNotAllowed
from sqlalchemy import Column, Integer, String, DateTime, Interval, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Reservation(Base):
    """The Reservation class holds room reservations and running conferences."""

    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Interval)
    timezone = Column(String)
    pin = Column(String)
    mail_owner = Column(String)
    active = Column(Boolean, default=False)

    def __repr__(self):
        return f'<Reservation(id={self.id}, name={self.name}, start_time={self.start_time})>'

    def from_dict(self, data: dict):
        """Set the data for this event with a dictionary. Use with the REST API and frontend."""

        self.name = data.get('name').replace(' ', '_').lower()
        self.mail_owner = data.get('mail_owner')
        self.pin = data.get('pin')
        self.timezone = data.get('timezone', 'UTC')
        self.set_start_time(start_time=data.get('start_time'))
        self.set_duration(duration=data.get('duration', -1))
        self.jitsi_server = os.environ.get('PUBLIC_URL')  # Public URL of the Jitsi web service

        return self

    def set_start_time(self, start_time: Union[datetime, str]):
        """Set the conference start time and make it timezone-aware"""

        if isinstance(start_time, datetime):
            start_time = start_time
        else:
            start_time = dp.isoparse(start_time)
        timezone = pytz.timezone(self.timezone)
        if (start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None):
            start_time = timezone.localize(start_time)
        self.start_time = start_time

    def set_duration(self, duration: Union[timedelta, str], default: int = 21600):
        """Set the conference duration and the conference end time"""

        if isinstance(duration, timedelta):
            self.duration = duration
        else:
            duration = int(duration) if int(duration) > 0 else default
            self.duration = timedelta(seconds=duration)
        self.end_time = self.start_time + self.duration

    @property
    def start_time_formatted(self) -> str:
        """Get the timezone-aware start date formatted for the frontend"""

        return self.start_time_aware.strftime('%d %b %Y - %H:%M %Z')

    @property
    def end_time_formatted(self) -> str:
        """Get the timezone-aware end date formatted for the frontend"""

        return self.end_time_aware.strftime('%d %b %Y - %H:%M %Z')

    @property
    def start_time_aware(self) -> datetime:
        """Get the timezone-aware start date"""

        timezone = pytz.timezone(self.timezone)
        return timezone.localize(self.start_time)

    @property
    def end_time_aware(self) -> datetime:
        """Get the timezone-aware end date"""

        timezone = pytz.timezone(self.timezone)
        return timezone.localize(self.end_time)

    @property
    def room_url(self):
        """Get the URL to the conference room.
        Only works if the environment variable PUBLIC_URL is set.
        """

        if self.jitsi_server is not None:
            return f'{self.jitsi_server}/{self.name}'
        else:
            return '/'

    def get_SimpleDateFormat_start_time(self) -> str:
        """Get a Java SimpleDateFormat compatible date string.
        Disgusting hack to make isoformat() print the precision time in milliseconds instead of
        microseconds, becasue Java can't handle that. -.-
        """

        start_time = self.start_time_aware.strftime('%Y-%m-%dT%H:%M:%S.ms%z')

        return start_time.replace('ms', '{:03.0f}'.format(self.start_time.microsecond//1000))

    def get_duration_in_seconds(self) -> int:
        """Get the conference duration in seconds."""

        return int(self.duration.total_seconds())

    def get_jicofo_api_dict(self) -> dict:
        """Return the information about the event as dict for Jicofo"""

        output = {
            'id': self.id,
            'name': self.name,
            'start_time': self.get_SimpleDateFormat_start_time(),
            'duration': self.get_duration_in_seconds()
        }
        if self.mail_owner is not None:
            output['mail_owner'] = self.mail_owner
        if self.pin is not None:
            output['pin'] = self.pin

        return output

    def check_allowed(self, owner: str = None, start_time: str = None) -> bool:
        """Check if the conference is allowed to start.
        The conference is check for owner and/or starting time."""

        if start_time is None:
            start_time = datetime.now(datetime.timezone.utc).isoformat()
        if self.mail_owner != owner:
            raise ConferenceNotAllowed('This user is not allowed to start this conference!')
        if self.start_time_aware > dp.isoparse(start_time):
            raise ConferenceNotAllowed('The conference has not started yet.')

        return True
