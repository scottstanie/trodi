"""
This module exports a Log class that wraps the logging python package

Uses the standard python logging utilities, just provides
nice formatting out of the box.

Usage:

    from apertools.log import get_log
    logger = get_log()

    logger.info("Something happened")
    logger.warning("Something concerning happened")
    logger.error("Something bad happened")
    logger.critical("Something just awful happened")
    logger.debug("Extra printing we often don't need to see.")
    # Custom output for this module:
    logger.success("Something great happened: highlight this success")
"""
from functools import wraps
import logging
import time

try:
    from colorlog import ColoredFormatter

    COLORS = True
except ImportError:
    from logging import Formatter

    COLORS = False


def get_log(debug=False, name=__file__, verbose=False):
    logger = logging.getLogger(name)
    return format_log(logger, debug=debug, verbose=verbose)


def format_log(logger, debug=False, verbose=False):
    log_level = logging.DEBUG if debug else logging.INFO
    log_colors = {
        "DEBUG": "blue",
        "INFO": "black",
        "WARNING": "red",
        "ERROR": "red",
        "CRITICAL": "black,bg_red",
    }

    if COLORS:
        format_ = "[%(asctime)s] [%(log_color)s%(levelname)s %(filename)s%(reset)s] %(message)s%(reset)s"
        formatter = ColoredFormatter(
            format_, datefmt="%m/%d %H:%M:%S", log_colors=log_colors
        )
    else:
        format_ = "[%(asctime)s] [%(levelname)s %(filename)s] %(message)s"
        formatter = Formatter(format_, datefmt="%m/%d %H:%M:%S")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)
        logger.setLevel(log_level)

        if verbose:
            logger.info("Logger initialized: %s" % (logger.name,))

    if debug or verbose:
        logger.setLevel(logging.DEBUG)

    return logger


logger = get_log()


def log_runtime(f):
    """
    Logs how long a decorated function takes to run
    Args:
        f (function): The function to wrap
    Retruns:
        function: The wrapped function
    """
    # pass function's docstring through
    @wraps(f)
    def wrapper(*args, **kwargs):
        t1 = time.time()
        result = f(*args, **kwargs)
        t2 = time.time()
        elapsed_time = t2 - t1

        time_string = "Total elapsed time for {} : {} minutes ({} seconds)".format(
            f.__name__,
            "{0:.2f}".format(elapsed_time / 60.0),
            "{0:.2f}".format(elapsed_time),
        )
        logger.info(time_string)
        return result

    return wrapper
