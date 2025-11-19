import sys, logging


# Filter out logs with the following strings to keep logs more concise
class LogFilter(logging.Filter):
    def filter_log(self, record):
        return (
            not [
                "guild_available",
                "presence_update",
                "socket_event_type",
            ]
            in record.getMessage()
        )


def log():
    # Create logger
    client_logger = logging.getLogger("nextcord.client").addFilter(LogFilter())
    state_logger = logging.getLogger("nextcord.state").addFilter(LogFilter())

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
