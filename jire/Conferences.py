from typing import Union
from .CustomExceptions import ConferenceExists, OverlappingReservation
from sqlalchemy import between, or_, create_engine
from sqlalchemy.orm import sessionmaker
from .Reservation import Base, Reservation
import logging

Session = sessionmaker()


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

    def check_overlapping_conference(self, event: Reservation) -> bool:
        """Check if start and end time of the new entry overlap with an existing reservation."""

        time_filter = between(event.start_time, Reservation.start_time, Reservation.end_time)
        result = self.session.query(Reservation) \
                             .filter(Reservation.name == event.name) \
                             .filter(time_filter) \
                             .filter(Reservation.active == True) \
                             .first()

        if result is not None:
            message = f'A conference with this name currently exists. Your reservation can only \
                        start once the event is over, which will be at {result.end_time_formatted}'
            raise ConferenceExists(message=message)

        return True

    def check_overlapping_reservations(self, event: Reservation) -> bool:
        """Check if start time of the new entry overlaps with existing conferences."""

        results = self.session.query(Reservation) \
                             .filter(Reservation.name == event.name) \
                             .filter(event.start_time <= Reservation.end_time) \
                             .filter(event.end_time >= Reservation.start_time) \
                             .filter(Reservation.active == False)

        if results.count():
            raise OverlappingReservation(events=results.all())

        return True
