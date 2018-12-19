#!/usr/bin/env python3
# Python 3.6

import time
import logging
from .constants import LOG_LEVEL

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

def timefunc(f):
    def f_timer(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        logger.info(f.__name__ + ' took ' + str(end - start))
        return result
    return f_timer
