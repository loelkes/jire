from datetime import datetime, timedelta
from dateutil import parser as dp
import os
import logging
import random
import pytz
from typing import Union
from .CustomExceptions import ConferenceNotAllowed, ConferenceExists


class Reservation:
    """The Reservation class holds room reservations and running conferences."""

    @staticmethod
    def format_event(input: dict) -> dict:
        """Format the event for frontend template.

        Formatting could be done in the teamplte or in the brower as well but it seemed easier and
        faster to just do it here.
        """

        item = input.copy()
        item['start_time'] = dp.isoparse(item['start_time']).strftime('%c')
        item['duration'] = str(timedelta(seconds=item['duration'])) if item['duration'] > 0 else ''
        return item

    def __init__(self, data: dict = None):

        self.id = int(data.get('id', random.random()*10e9))
        self.name = data.get('name').replace(' ', '_').lower()
        self.mail_owner = data.get('mail_owner')
        self.timezone = pytz.timezone(data.get('timezone', 'UTC'))
        _duration = int(data.get('duration', -1))
        _duration = 6*3600 if _duration <= 0 else _duration
        self.__duration = timedelta(seconds=_duration)
        self.jitsi_server = os.environ.get('PUBLIC_URL')  # Public URL of the Jitsi web service

        # Make it possible to pass datetime instances. Maybe for the future...
        if isinstance(data.get('start_time'), datetime):
            self.__start_time = data.get('start_time')
        else:
            self.__start_time = dp.isoparse(data.get('start_time'))
        # Only set timezone if datetime is naive
        if (self.__start_time.tzinfo is None or
                self.__start_time.tzinfo.utcoffset(self.__start_time) is None):
            self.__start_time = self.timezone.localize(self.__start_time)

    @property
    def room_url(self):
        if self.jitsi_server is not None:
            return f'{self.jitsi_server}/{self.name}'
        else:
            return '/'

    @property
    def start_time(self) -> str:
        """Get a Java SimpleDateFormat compatible date string."""

        return self.__start_time.isoformat().replace('000+', '+')
        # Disgusting hack to make isoformat() print the precision time in milliseconds instead
        # of microseconds, becasue Java can't handle that. -.-

    @property
    def duration(self) -> int:
        """Get the conference duration in seconds.

        If not set the duration falls back to 6 hours (21.600 seconds). 
        """

        return int(self.__duration.total_seconds())

    def to_dict(self) -> dict:
        """Return the information about the event as dict"""

        output = {
            'id': self.id,
            'name': self.name,
            'start_time': self.start_time,
            'duration': self.duration
        }
        if self.mail_owner is not None:
            output['mail_owner'] = self.mail_owner
        if self.room_url is not None:
            output['url'] = self.room_url
        return output

    def check_allowed(self, owner: str = None, start_time: str = None) -> bool:
        """Check if the conference is allowed to start.

        The conference is check for owner and/or starting time."""
        if start_time is None:
            start_time = datetime.now(datetime.timezone.utc).isoformat()
        if self.mail_owner != owner:
            raise ConferenceNotAllowed('This user is not allowed to start this conference!')
        if self.__start_time > dp.isoparse(start_time):
            raise ConferenceNotAllowed('The conference has not started yet.')
        return True


class Manager:
    def __init__(self):
        self.__logger = logging.getLogger()
        self.__conferences = {}
        self.__reservations = {}

    @property
    def reservations(self) -> dict:
        """Get all reservations as dict"""

        return self.__reservations

    @property
    def conferences_formatted(self) -> dict:
        """Get all conferences formatted for the frontend"""

        return {key: Reservation.format_event(val) for key, val in self.__conferences.items()}

    @property
    def reservations_formatted(self) -> dict:
        """Get all reservations formatted for the frontend"""

        return {key: Reservation.format_event(val) for key, val in self.__reservations.items()}

    @property
    def conferences(self) -> dict:
        """Get all conferences as dict"""

        return self.__conferences

    def search_conference_by_name(self, name: str) -> Union[None, str]:
        """Return the confernce ID for a given name"""

        for id, conference in self.conferences.items():
            if conference.get('name') == name:
                return id
        return None

    def allocate(self, data: dict) -> dict:
        """Check if the conference request matches a reservation."""

        # Check for conflicting conference
        name = data.get('name')
        id = self.search_conference_by_name(name)
        if id is not None:
            self.__logger.info(f'Conference {id} already exists')
            raise ConferenceExists(id)
        # Check for existing reservation
        if name in self.reservations:
            # Raise ConferenceNotAllowed if necessary
            reservation = Reservation(self.reservations.get(name))
            reservation.check_allowed(owner=data.get('mail_owner'),
                                      start_time=data.get('start_time'))
            self.__logger.debug('Reservation checked, conference can start')
            self.__conferences[reservation.id] = self.__reservations.pop(name)
            return reservation.to_dict()

        self.__logger.debug(f'No reservation found for room name {name}')
        id = self.add_conference(data)
        return self.__conferences[id]

    def delete_conference(self, id: int = None) -> bool:
        """Delete a conference in the database"""

        try:
            self.__conferences.pop(int(id))
        except KeyError:
            self.__logger.error(f'Could not remove conference {id} from the database')
            return False
        else:
            self.__logger.debug(f'Remove conference {id} from the database')
            return True

    def add_conference(self, data: dict) -> str:
        """Add a conference to the database"""

        conference = Reservation(data)
        self.__conferences[conference.id] = conference.to_dict()
        self.__logger.debug(f'Add conference {conference.id} - {conference.name} to the database')
        return conference.id

    def get_conference(self, id: int = None) -> dict:
        """Get the conference information"""

        if id in self.__conferences:
            return self.__conferences.get(id)
        return {}

    def delete_reservation(self, id: int = None, name: str = None) -> bool:
        """Delete a reservation in the database"""

        if id is not None:
            for rname, reservation in self.__reservations.items():
                if reservation.get('id') == int(id):
                    name = rname
                    break
        try:
            self.__reservations.pop(name)
        except KeyError:
            self.__logger.error(f'Could not remove reservation {name} from the database')
            return False
        else:
            self.__logger.debug(f'Remove reservation {name} from the database')
            return True

    def add_reservation(self, data: dict) -> int:
        """Add a reservation to the database."""

        reservation = Reservation(data)
        print(reservation.to_dict())
        self.__reservations[reservation.name] = reservation.to_dict()
        self.__logger.debug(f'Add reservation for room {reservation.name} to the database')
        return reservation.id
