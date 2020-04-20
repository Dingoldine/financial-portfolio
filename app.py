from scrapers import avanza_scraper, nasdaq_omx_scraper, event_watcher
from portfolio import Portfolio
from multiprocessing import Process

import time

def run():
    fileWatcherProcess = Process(target=event_watcher.startObserver, args=())
    fileWatcherProcess.start()
    # avanza_scraper.scrape()
    # nasdaq_omx_scraper.scrape()
    # nasdaq_omx_scraper.saveStockInfoToExcel()

    P = Portfolio()
    # P.checkRules()
    # P.fundsBreakdown()
    P.stocksBreakdown()

    fileWatcherProcess.terminate()
run()
