import logging
import logging.config
from config.conf import *

def get_logger():

    logging.config.dictConfig(log_config)

    log = logging.getLogger()

    return log
