from hsciMain import hsciMain
from config import log

if __name__ == "__main__":
    logger = log.get_logger()
    try:
        hsciMain.hsciMain()
    except Exception as e:
        logger.critical(e, exc_info=True)
