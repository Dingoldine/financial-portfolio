from celery import Celery, chain, chord, group 
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from scrapers import avanza_scraper, nasdaq_omx_scraper, degiro_scraper
from portfolio import Portfolio
from database import Database
import celeryconfig
from celery.signals import worker_process_init, worker_process_shutdown
import configparser
import time, sys 
Config = configparser.ConfigParser()
Config.read('./config.ini')


if (Config["NETWORK-MODE"]["localhost"] == True):
    celery_broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
    celery_backend = 'redis://localhost:6379/0' 
else:
    celery_broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@{Config["CELERY"]["RABBITMQ_HOSTNAME"]}'
    celery_backend = f'redis://{Config["REDIS"]["REDIS_HOSTNAME"]}:6379/0'
# Create the celery app and get the logger
try:
    celery_app = Celery('portfolio_worker', broker=celery_broker, backend=celery_backend)
    celery_app.config_from_object(celeryconfig)
except:
    print("Could not configure celery")
    sys.exit(-1)


db = None

@worker_process_init.connect
def init_worker(**kwargs):
    global db
    try:
        print('Initializing database connection for worker.')
        db = Database()
        db.connect()
    except Exception:
        raise

@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global db
    if db:
        print('Closing database connectionn for worker.')
        db.disconnect()


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


@celery_app.task(bind=True, serializer='json')

def updateDBTEST(self, portfolio):
    logger.info("----Updating db----")
    #logger.info(portfolio)
    try:
        time.sleep(5)
        return {'message': 'job completed successfully'} 
    except Exception:
        raise

@celery_app.task(bind=True, serializer='json')
def updateDB(self, portfolio):
    logger.info("----Updating db----")
    #logger.info(portfolio)
    try:
        #db.createTableFromDF(portfolio.get('stocks'), "stocks")
        #db.createTableFromDF(portfolio.get('funds'), "funds")
        db.createTableFromDF(portfolio.get('portfolio'), "portfolio")
        logger.info("----Updating db completed successfully----")
        return {'message': 'job completed successfully'} 
    except Exception as e:
        logger.exception("Error", exc_info=e)
        raise

@celery_app.task(bind=True, serializer='json')
def scrapeAvanza(self):
    logger.info("LOGGING TASK SCRAPING AVANZA: %s", )
    return avanza_scraper.scrape(db)

@celery_app.task(bind=True, serializer='json')
def scrapeDegiro(self, something=""):
    logger.info("LOGGING TASK SCRAPING DEGIRO: %s", )
    return degiro_scraper.scrapeTEST()

@celery_app.task(bind=True, serializer="json")
def constructPortfolio(self, parameter_list):
    #logger.info(parameter_list)
    (avanzaHoldings, degiroHoldings) = parameter_list

    P = Portfolio(avanzaHoldings, degiroHoldings)
    #P.stocksBreakdown()
    #P.fundsBreakdown()
    return {
        #'stocks': P.getStocks().to_json(orient='index'),
        #'funds': P.getFunds().to_json(orient='index'),
        'portfolio': P.getPortfolio().to_json(orient='index')
    }


@celery_app.task(bind=True, serializer='json')
def updatePortfolio(self):
    try:
        workflow = chain([
            chord([scrapeAvanza.s(),scrapeDegiro.s()], constructPortfolio.s()),
            updateDB.s()
        ])

        res = workflow()
  
        return res

    except (Exception) as exc:
        logger.exception("Error", exc_info=exc)
        raise self.retry(exc=exc, countdown=5, max_retries=1) #retry in 5 seconds
