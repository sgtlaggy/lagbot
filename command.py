"""Module containing Command class."""


class Command():
    """Command class."""

    def __init__(self, name, func, servers):
        """Command constructor."""
        self.name = name
        self.func = func
        self.serv = servers

    def __str__(self):
        """String representation of Command."""
        return self.name
