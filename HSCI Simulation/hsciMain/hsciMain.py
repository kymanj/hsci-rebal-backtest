from config.conf import *
from config import log
from func import updateHSCI
from func import backtestHSCI
import os

logger = log.get_logger()

def hsciMain():
    logger.info('Start running hsciMain')

    # get HSCI Historical Change File
    update_hsci = simulation_params["update_hsci_file"]
    download_path = working_directories['raw_data_files']
    download_hsci_file_path = working_directories["raw_data_files"] + "/" + simulation_params["hsci_file_name"]
    if update_hsci:
        logger.info("Start updating HSCI Historical Change File")

        if os.path.exists(download_hsci_file_path):
            os.remove(download_hsci_file_path)
            logger.info("Deleted old HSCI Historical Change File")

        updateHSCI.scrape_hsci_change(download_path=download_path, download_hsci_file_path=download_hsci_file_path,
                                      chrome_driver_path=chrome_driver_path)
        logger.info('''
        Updated HSCI Historical Change File. Path:
        %s
        ''' % (download_hsci_file_path))
    else:
        logger.info("Use existing HSCI Historical Change File")

        if not os.path.exists(download_hsci_file_path):
            raise Exception('''
            No existing HSCI Historical Change File. 
            Please change update_hsci_file to True in config.conf - simulation_params
            ''')

    # get a Trading Log from HSCI Historical Change File
    start_year = simulation_params["start_year"]
    end_year = simulation_params["end_year"]
    begin_business_day = simulation_params["begin_business_day"]
    end_business_day = simulation_params["end_business_day"]

    logger.info("Start getting HSCI Trade File")
    main_file = updateHSCI.get_hsci_trade_file(start_year=start_year, end_year=end_year,
                                               begin_business_day=begin_business_day, end_business_day=end_business_day,
                                               download_hsci_file_path=download_hsci_file_path).run()
    # clean HSCI Trade File
    logger.info("Start cleaning HSCI Trade File")
    main_file = backtestHSCI.clean_trade_file(trade_file=main_file, reuse_ticker_dict=reuse_ticker_dict).run()

    # get adjusted Trading Log and Backtesting File
    logger.info("Start getting Final Trading Log and BackTesting File")
    funding_source = simulation_params["funding_source"]
    output_hsci_trade_file_path = working_directories["output_files"] + "/" + simulation_params["trade_file_name"]
    output_hsci_backtest_file_path = working_directories["output_files"] + "/" + simulation_params["backtest_file_name"]
    backtestHSCI.get_backtest_files(trade_file=main_file,
                                    funding_source=funding_source,
                                    output_hsci_trade_file_path=output_hsci_trade_file_path,
                                    output_hsci_backtest_file_path=output_hsci_backtest_file_path).run()

if __name__ == "__main__":
    hsciMain()