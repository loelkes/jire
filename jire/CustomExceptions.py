class ConferenceExists(Exception):
    """Raised if the conference already exists."""

    def __init__(self, id=None):
        self.id = id


class ConferenceNotAllowed(Exception):
    """Raised if the user is not allowed to create the conference."""

    def __init__(self, message=None):
        self.message = message
