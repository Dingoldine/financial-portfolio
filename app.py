from scrapers import avanza_scraper, nasdaq_omx_scraper
from portfolio import Portfolio



def run():
    #avanza_scraper.scrape()
    #nasdaq_omx_scraper.scrape()
    P = Portfolio()
    P.checkRules()
    P.fundsBreakdown()
    P.stocksBreakdown()

run()
