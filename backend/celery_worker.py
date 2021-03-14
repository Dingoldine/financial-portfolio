from celery import Celery, chain, chord
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from scrapers import avanza_scraper, nasdaq_omx_scraper
from database import Database
from portfolio import Portfolio
from database import Database
import configparser
import time, sys
Config = configparser.ConfigParser()
Config.read('./config.ini')


if (Config["MODE"]["development"]):
    broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
else:
    broker = "my-cloudampq-broker"

# Create the celery app and get the logger
try:
    celery_app = Celery('tasks', broker=broker)
    celery_app.conf.update(
        accept_content=['json', 'pickle', 'application/x-python-serialize'],
        timezone='Europe/Stockholm',
        enable_utc=True
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

@celery_app.task(bind=True, serializer='pickle')
def scrapeAvanza(self):
    logger.info("LOGGING EXTRA INFO PARAMETER: %s", )
    return avanza_scraper.scrape()


@celery_app.task(bind=True, serializer='pickle')
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
        
        res = chain(scrapeAvanza.s(), constructPortfolio.s(),updateDB.s())()
        return res
        #logger.info("Scraping complete:, response: %s" % (res))
        # time.sleep(1)
        # self.update_state(state="PROGRESS", meta={'progress': 50})
        # time.sleep(1)
        # self.update_state(state="PROGRESS", meta={'progress': 90})
        # time.sleep(1)
    # Avanza.FailWhaleError, Avanza.LoginError
    except (Exception) as exc:
         raise self.retry(exc=exc, countdown=5, max_retries=2) #retry in 5 seconds
