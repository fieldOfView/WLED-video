import logging
from colorlog import ColoredFormatter


def logger_handler():
    """'
    ## logger_handler

    Returns the logger handler

    **Returns:** A logger handler
    """

    formatter = ColoredFormatter(
        "{green}{asctime}{reset} :: {bold_purple}{name:^13}{reset} :: {log_color}{levelname:^8}{reset} :: {bold_white}{message}",
        datefmt="%H:%M:%S",
        reset=True,
        log_colors={
            "INFO": "bold_cyan",
            "DEBUG": "bold_yellow",
            "WARNING": "bold_red,fg_thin_yellow",
            "ERROR": "bold_red",
            "CRITICAL": "bold_red,bg_white",
        },
        style="{",
    )

    handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    return handler
