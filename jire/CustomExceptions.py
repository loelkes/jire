class ConferenceExists(Exception):
    """Raised if the conference already exists."""

    def __init__(self, id=None, message=None):
        self.id = id
        self.message = 'This room already exists.'


class ConferenceNotAllowed(Exception):
    """Raised if the user is not allowed to create the conference."""

    def __init__(self, message=None):
        self.message = message

class OverlappingReservation(Exception):

    def __init__(self, message=None, events=[]):
        self.events = events
        self.message = message or 'The room is not available at the selected time.'
