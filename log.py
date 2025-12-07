import sys, logging


class LogFilter(logging.Filter):
    def filter(self, record):
        black_list = [
            "socket_event_type",
            "presence_update",
            "guild_available",
            "Dispatching event",
        ]
        return not any(banned_str in record.getMessage() for banned_str in black_list)


def log():
    # Create logger
    client_logger = logging.getLogger("nextcord.client")
    state_logger = logging.getLogger("nextcord.state")

    # Add filters
    client_logger.addFilter(LogFilter())
    state_logger.addFilter(LogFilter())

    # Format log entries
    FORMAT = "[{asctime}][{filename}][{lineno:3}][{funcName}][{levelname}] {message}"
    formatter = logging.Formatter(FORMAT, style="{")

    # Create file handler to write to the log
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler("latest.log", mode="w")

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add file handler to logger
    client_logger.addHandler(console_handler)
    state_logger.addHandler(console_handler)

    client_logger.addHandler(file_handler)
    state_logger.addHandler(file_handler)

    client_logger.setLevel(logging.DEBUG)
    state_logger.setLevel(logging.DEBUG)
