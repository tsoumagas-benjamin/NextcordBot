import sys
import logging
import pytz
from datetime import datetime


class LogFilter(logging.Filter):
    def filter(self, record):
        black_list = [
            "socket_event_type",
            "presence_update",
            "guild_available",
            "Dispatching event",
        ]
        return not any(banned_str in record.getMessage() for banned_str in black_list)


class Formatter(logging.Formatter):
    """override logging.Formatter to use an aware datetime object"""

    def converter(self, timestamp):
        # Create datetime in UTC
        local_time = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        # Change datetime's timezone
        return local_time.astimezone(pytz.timezone("Canada/Eastern"))

    def formatTime(self, record, datefmt=None):
        local_time = self.converter(record.created)
        if datefmt:
            s = local_time.strftime(datefmt)
        else:
            try:
                s = local_time.isoformat(timespec="milliseconds")
            except TypeError:
                s = local_time.isoformat()
        return s


def log():
    # Create logger
    client_logger = logging.getLogger("nextcord.client")
    state_logger = logging.getLogger("nextcord.state")

    # Add filters
    client_logger.addFilter(LogFilter())
    state_logger.addFilter(LogFilter())

    # Create file handler to write to the log
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler("latest.log", mode="w")

    # Format log entries
    FORMAT = "[{asctime}][{filename}][{lineno:3}][{funcName}][{levelname}] {message}"
    formatter = file_handler.setFormatter(
        Formatter(FORMAT, "%Y-%m-%d %H:%M:%S", style="{")
    )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add file handler to logger
    client_logger.addHandler(console_handler)
    state_logger.addHandler(console_handler)

    client_logger.addHandler(file_handler)
    state_logger.addHandler(file_handler)

    client_logger.setLevel(logging.DEBUG)
    state_logger.setLevel(logging.DEBUG)
