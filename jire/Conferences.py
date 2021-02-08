from datetime import datetime, timedelta
from dateutil import parser as dp
import os
import logging
import random
import pytz
from typing import Union
from .CustomExceptions import ConferenceNotAllowed, ConferenceExists, OverlappingReservation
from sqlalchemy import Column, Integer, String, DateTime, Interval, Boolean, create_engine, or_
from sqlalchemy import between
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


Base = declarative_base()
Session = sessionmaker()

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
        return f'<Reservation(id={self.id}, name={self.name}), start_time={self.start_time}>'

    def from_dict(self, data: dict):
        self.name = data.get('name').replace(' ', '_').lower()
        self.mail_owner = data.get('mail_owner')
        self.pin = data.get('pin')
        self.timezone = data.get('timezone', 'UTC')
        self.set_start_time(start_time=data.get('start_time'))
        self.set_duration(duration=data.get('duration', -1))
        self.jitsi_server = os.environ.get('PUBLIC_URL')  # Public URL of the Jitsi web service

        return self

    def set_start_time(self, start_time: Union[datetime, str]):
        """Handle different datetime inputs and timezones"""

        if isinstance(start_time, datetime):
            start_time = start_time
        else:
            start_time = dp.isoparse(start_time)
        timezone = pytz.timezone(self.timezone)
        if (start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None):
            start_time = timezone.localize(start_time)
        self.start_time = start_time

    def set_duration(self, duration: Union[timedelta, str]):
        if isinstance(duration, timedelta):
            self.duration = duration
        else:
            duration = int(duration) if int(duration) > 0 else 6*36000
            self.duration = timedelta(seconds=duration)
        self.end_time = self.start_time + self.duration

    @property
    def start_time_formatted(self) -> str:

        return self.start_time_aware.strftime('%d %b %Y - %H:%M %Z')

    @property
    def end_time_formatted(self) -> str:

        return self.end_time_aware.strftime('%d %b %Y - %H:%M %Z')

    @property
    def start_time_aware(self) -> datetime:

        timezone = pytz.timezone(self.timezone)
        return timezone.localize(self.start_time)

    @property
    def end_time_aware(self) -> datetime:

        timezone = pytz.timezone(self.timezone)
        return timezone.localize(self.end_time)

    @property
    def room_url(self):

        if self.jitsi_server is not None:
            return f'{self.jitsi_server}/{self.name}'
        else:
            return '/'

    def get_SimpleDateFormat_start_time(self) -> str:
        """Get a Java SimpleDateFormat compatible date string.

        Disgusting hack to make isoformat() print the precision time in milliseconds instead of
        microseconds, becasue Java can't handle that. -.-
        """

        start_time = self.start_time.strftime('%Y-%m-%dT%H:%M:%S.ms%z')

        return start_time.replace('ms', '{:03.0f}'.format(self.start_time.microsecond//1000))


    def get_duration_in_seconds(self) -> int:
        """Get the conference duration in seconds."""

        return int(self.__duration.total_seconds())

    def get_jicofo_api_dict(self) -> dict:
        """Return the information about the event as dict for Jicofo"""

        output = {
            'id': self.id,
            'name': self.name,
            'start_time': self.get_SimpleDateFormat_start_time(),
            'duration': str(self.duration)
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


class Manager:
    def __init__(self):
        self.__logger = logging.getLogger()
        engine = create_engine('sqlite:///data/reservations.sqlite3', echo=False)
        Base.metadata.create_all(engine)
        Session.configure(bind=engine)
        self.session = Session()

    @property
    def all_reservations(self) -> list:
        """Get all reservations as dict"""

        return self.session.query(Reservation) \
                           .filter(Reservation.active == False) \
                           .order_by(Reservation.id)

    @property
    def all_conferences(self) -> list:
        """Get all conferences as dict"""

        return self.session.query(Reservation) \
                           .filter(Reservation.active == True) \
                           .order_by(Reservation.id)


    def allocate(self, data: dict) -> dict:
        """Check if the conference request matches a reservation."""

        # Check for conflicting conference
        name = data.get('name')
        event = self.get_conference(name=name)
        if event is not None:
            self.__logger.info(f'Conference {event.id} already exists')
            raise ConferenceExists(event.id)
        # Check for existing reservation
        event = self.get_reservation(name=name)
        if event is not None:
            # Raise ConferenceNotAllowed if necessary
            event.check_allowed(owner=data.get('mail_owner'),
                                start_time=data.get('start_time'))
            self.__logger.debug('Reservation for room {name} checked, conference can start.')
            event.active = True
            self.session.commit()
        else:
            self.__logger.debug(f'No reservation found for room {name}')
            event = self.add_conference(data)

        return event.get_jicofo_api_dict()

    def delete_conference(self, id: int = None, name: str = None) -> bool:
        """Delete a conference in the database"""

        event = self.session.query(Reservation) \
                            .filter(or_(Reservation.name == name, Reservation.id == id)) \
                            .filter(Reservation.active == True) \
                            .first()

        if event is None:
            self.__logger.error('Delete failed, could not find conference in database')
            return False

        self.session.delete(event)
        self.session.commit()
        return True

    def add_conference(self, data: dict) -> str:
        """Add a conference to the database"""

        event = Reservation().from_dict(data)
        event.active = True
        self.session.add(event)
        self.session.commit()
        self.__logger.debug(f'Add conference {event.id} - {event.name} to the database')
        return event

    def get_conference(self, id: int = None, name: str = None) -> Union[Reservation, None]:
        """Get the conference information"""

        return self.session.query(Reservation) \
                           .filter(or_(Reservation.name == name, Reservation.id == id)) \
                           .filter(Reservation.active == True) \
                           .first()


    def delete_reservation(self, id: int = None, name: str = None) -> bool:
        """Delete a reservation in the database"""

        event = self.session.query(Reservation) \
                            .filter(or_(Reservation.name == name, Reservation.id == id)) \
                            .first()

        if event is None:
            self.__logger.error('Delete failed, could not find reservation in database')
            return False

        self.session.delete(event)
        self.session.commit()
        return True

    def get_reservation(self, id: int = None, name: str = None) -> Union[Reservation, None]:
        """Get the reservation information"""

        return self.session.query(Reservation) \
                           .filter(or_(Reservation.name == name, Reservation.id == id)) \
                           .filter(Reservation.active == False) \
                           .first()

    def add_reservation(self, data: dict) -> int:
        """Add a reservation to the database."""

        event = Reservation().from_dict(data)
        self.check_overlapping_reservations(event)
        self.session.add(event)
        self.session.commit()
        self.__logger.debug(f'Add reservation for room {event.name} to the database')
        return event

    def check_overlapping_conference(self, new_res: Reservation) -> bool:

        time_filter = between(new_res.start_time, Reservation.start_time, Reservation.end_time)
        result = self.session.query(Reservation) \
                             .filter(Reservation.name == new_res.name) \
                             .filter(time_filter) \
                             .filter(Reservation.active == True) \
                             .first()

        if result is not None:
            message = f'A conference with this name currently exists. Your reservation can only \
                        start once the event is over, which will be at {result.end_time_formatted}'
            raise ConferenceExists(message=message)

        return True

    def check_overlapping_reservations(self, new_res: Reservation) -> bool:

        # Check if start and end time of the new reservation collide with other bookings
        time_filter = or_(between(new_res.start_time, Reservation.start_time, Reservation.end_time),
                          between(new_res.end_time, Reservation.start_time, Reservation.end_time))

        results = self.session.query(Reservation) \
                             .filter(Reservation.name == new_res.name) \
                             .filter(time_filter) \
                             .filter(Reservation.active == False)

        if results.count():
            raise OverlappingReservation(events=results.all())

        return True
