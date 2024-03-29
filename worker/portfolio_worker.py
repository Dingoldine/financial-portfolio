from celery import Celery, chain, chord
from celery.utils.log import get_task_logger
from scrapers import avanza_scraper, degiro_scraper
from portfolio import Portfolio
from database import Database
import celeryconfig
from celery.signals import worker_process_init, worker_process_shutdown
import configparser
import time
import sys
Config = configparser.ConfigParser()
Config.read('./config.ini')

# Connection details
if Config["NETWORK-MODE"]["localhost"] is True:
    CELERY_BROKER = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
    CELERY_BACKEND = 'redis://localhost:6379/0'
else:
    CELERY_BROKER = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@{Config["CELERY"]["RABBITMQ_HOSTNAME"]}'
    CELERY_BACKEND = f'redis://{Config["REDIS"]["REDIS_HOSTNAME"]}:6379/0'

# Create the celery app and get  logger
try:
    celery_app = Celery('portfolio_worker',
                        broker=CELERY_BROKER, backend=CELERY_BACKEND)
    celery_app.config_from_object(celeryconfig)

    logger = get_task_logger(__name__)

    db = None

except Exception:
    print("Could not configure celery")
    sys.exit(-1)


# Initialize db connection on startup
@worker_process_init.connect
def init_worker(**kwargs):
    global db
    try:
        print('Initializing database connection for worker.')
        db = Database()
        db.connect()
    except Exception:
        raise


# Disconnect from db on shutdown
@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global db
    if db:
        print('Closing database connectionn for worker.')
        db.disconnect()


@celery_app.task(bind=True, serializer='json')
def updateDBTEST(self, portfolio):
    logger.info("----Updating db----")
    try:
        time.sleep(5)
        return {'message': 'job completed successfully'}
    except Exception:
        raise


@celery_app.task(bind=True, serializer='json')
def updateDB(self, portfolio):
    logger.info("----Updating db----")
    try:
        db.create_table_from_df(portfolio.get('portfolio'), "portfolio")
        logger.info("----Updating db completed successfully----")
        return {'message': 'job completed successfully'}
    except Exception as e:
        logger.exception("Error", exc_info=e)
        raise


@celery_app.task(bind=True, serializer='json')
def scrapeAvanza(self):
    try:
        logger.info("%s", "Clearing qr_table of old content")
        db.query("TRUNCATE TABLE qr_table;")
        db.commit()
        logger.info("Begin Selenium scraping")
        return avanza_scraper.scrape(db)
    except Exception as e:
        logger.exception("Error", exc_info=e)
        raise


@celery_app.task(bind=True, serializer='json')
def scrapeDegiro(self, something=""):
    logger.info("LOGGING TASK SCRAPING DEGIRO: %s", )
    return degiro_scraper.scrape()


@celery_app.task(bind=True, serializer="json")
def constructPortfolio(self, parameter_list):

    (avanzaHoldings, degiroHoldings) = parameter_list

    P = Portfolio(avanzaHoldings, degiroHoldings)

    return {
        'portfolio': P.getPortfolio().to_json(orient='index')
    }


@celery_app.task(bind=True, serializer='json')
def do_on_error(*args, **kwargs):
    logger.info("on_error_task: {}, {}".format(args, kwargs))
    return "OK do_on_error"


# Main Task
# Calls all subtasks in following order
# (scrapeAvanza, scrapeDegiro) in parallel -> constructPortfolio -> updateDB
@celery_app.task(bind=True, serializer='json')
def updatePortfolio(self):
    try:
        workflow = chain([
            chord([scrapeAvanza.s(), scrapeDegiro.s()], constructPortfolio.s()),
            updateDB.s()
        ]).on_error(do_on_error.s("Error caught by chain"))

        res = workflow()

        return res

    except (Exception) as exc:
        logger.exception("Error", exc_info=exc)
        # retry in 5 seconds
        raise self.retry(exc=exc, countdown=5, max_retries=1)
