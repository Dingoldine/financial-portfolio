from celery import Celery, chain, chord, group
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from scrapers import avanza_scraper, nasdaq_omx_scraper, degiro_scraper
from portfolio import Portfolio
from database import Database
import configparser
import time, sys
Config = configparser.ConfigParser()
Config.read('./config.ini')

if (Config["NETWORK-MODE"]["localhost"] == True):
    broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
else:
    broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@rabbit'

# Create the celery app and get the logger
try:
    celery_app = Celery('portfolio_worker', broker=broker)
    celery_app.conf.update(
        accept_content=['json', 'pickle', 'application/x-python-serialize'],
        timezone='Europe/Stockholm',
        enable_utc=True,
        result_backend='redis://redis:6379/0',
        task_routes = {
            'portfolio_worker.tasks.updatePortfolio': {
                'queue': 'default',
                'routing_key': 'default',
            },
        },
        task_default_queue = 'default',
        task_default_exchange_type = 'direct',
        task_default_routing_key = 'default'
    )
except:
    print("Could not connect to broker")
    sys.exit(-1)

logger = get_task_logger(__name__)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # Executes every Monday morning at 7:30 a.m.
    sender.add_periodic_task(
        crontab(hour=22, minute=14, day_of_week=3),
        updatePortfolio.s(),
    )

@celery_app.task
def add(x, y):
    res = x + y
    logger.info("Adding %s + %s, res: %s" % (x, y, res))
    return res

@celery_app.task(bind=True, serializer='pickle', ignore_result=True)
def updateDB(self, Portfolio):
    logger.info(Portfolio)
    logger.info("----Updating db----")
    try:
        db = Database()
        db.connect()
        db.createTableFromDF(Portfolio.getStocks(), "stocks")
        db.createTableFromDF(Portfolio.getFunds(), "funds")
        logger.info("----Updating db completed successfully----")
    except Exception:
        raise
    finally:
        db.disconnect()

@celery_app.task(bind=True)
def scrapeAvanza(self):
    logger.info("LOGGING TASK SCRAPING AVANZA: %s", )
    return avanza_scraper.scrape()

@celery_app.task(bind=True)
def scrapeDegiro(self):
    logger.info("LOGGING TASK SCRAPING DEGIRO: %s", )
    return degiro_scraper.scrapeTEST()

@celery_app.task(bind=True)
def constructPortfolio(self, parameter_list):
    logger.info(parameter_list)
    (dataframes, fundInfo) = parameter_list
    P = Portfolio(dataframes, fundInfo)
    P.stocksBreakdown()
    P.fundsBreakdown()
    return P


@celery_app.task(bind=True)
def updatePortfolio(self):
    try:
        res = chain(group([scrapeAvanza.s(),scrapeDegiro.s()]), chain(constructPortfolio.s(),updateDB.s()))()
        return res
        # logger.info("Scraping complete:, response: %s" % (res))
        # time.sleep(1)
        # self.update_state(state="PROGRESS", meta={'progress': 50})
        # time.sleep(1)
        # self.update_state(state="PROGRESS", meta={'progress': 90})
        # time.sleep(1)
    # Avanza.FailWhaleError, Avanza.LoginError
    except (Exception) as exc:
         raise self.retry(exc=exc, countdown=5, max_retries=2) #retry in 5 seconds
