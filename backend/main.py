from fastapi import FastAPI, Request, Response, Depends, BackgroundTasks 
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Database
from pydantic import BaseModel
from typing import Optional
from multiprocessing import Process
import time, configparser
from celery import Celery

Config = configparser.ConfigParser()
Config.read('./config.ini')

if (Config["NETWORK-MODE"]["localhost"] == True):
    broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
else:
    broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@rabbit'

db = None
P = None

app = FastAPI()

origins = [
    "http://frontend",
    "http://localhost:8080"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Dependency: db_conn Generator 
#The get_db() function ensures that any route passed this function ought
#to have our SessionLocal database connection when needed and that
#  the session is closed after use.
def get_db():
    try:
        db_conn = db.getLocalSession()
        yield db_conn
    finally:
        db_conn.close()

@app.on_event("startup")
async def startup():
    print("starting server....")
    try:
        print('Initializing database connection..')
        global db
        global P
        db = Database()
        db.connect()
        db.create()
        db.commit()
    except Exception:
        raise


@app.on_event("shutdown")
async def shutdown():
    print("server shutting down....")
    await db.disconnect()


@app.get("/getPortfolio")
def getPortfolio():
    data = db.fetch_portfolio()[0][0]
    performance = db.fetch_portfolio_performance()[0][0]
    return {"data": data, "performance": performance}

@app.get("/getFunds")
def getFunds():
    data = db.fetch_funds()
    columns = db.getColumnNames('funds')
    return {"data": data, "columns": columns}

@app.get("/getStocks")
def getStocks():
    data = db.fetch_stocks()[0][0] #for some reason the result is way nested
    return {"data": data}

@app.get("/doRefresh")
# I'm using fastAPI exactly like this, combining concurrent.futures.ProcessPoolExecutor() 
# and asyncio to manage long running jobs.
# If you don't want to rely on other modules (celery etc), 
# you need to manage yourself the state of your job, and store it somewhere. 
# I store it in the DB so that pending jobs can be resumed after 
# a restart of the server.
# Note that you must NOT perform CPU intensive computations in the background_tasks of the app,
# because it runs in the same async event loop that serves the requests and it will stall your app.
# Instead submit them to a thread pool or a process pool.
def doRefresh(dbSession: Session = Depends(get_db)):
    ## LOOK INTO CELERY, REDIS, EVENT STREAMS AND QUEUES ETC
    """     background_tasks(tasks=[
        avanza_scraper.scrape(),
        nasdaq_omx_scraper.scrape(),
        P.stocksBreakdown(),
        P.fundsBreakdown(),
        db.createTableFromDF(P.getStocks(), "stocks"),
        db.createTableFromDF(P.getFunds(), "funds")
    ])
     """
    celeryapp = Celery('portfolio_worker', broker=broker)
    #celeryapp.config_from_object('config.celeryconfig')


    r = celeryapp.send_task('portfolio_worker.updatePortfolio', args=())
    print(r.id)

    #res = updatePortfolio.delay()
    #print(res.status) # 'SUCCESS'
    #print(res.id) # '432890aa-4f02-437d-aaca-1999b70efe8d'
    return {"message": "update request received"}

class Stock(BaseModel):
    asset: str
    change: float
    currency: str
    isin: str
    latest_price: float
    market_value_sek: float
    profit:  Optional[float]
    purchase_price: float
    weight: float
    shares: int
    symbol: str
    asset_class: Optional[str]
@app.put('/updateStock')
def updateStock(stock: Stock, dbSession: Session = Depends(get_db)):
    print(stock)
    db.updatePortfolioTable(stock, dbSession)
    return {"message": "update successfull"}

@app.get("/resetDatabase")
def resetDatabase():
    db.reset()
    db.commit()
    return {"message": "reset complete"}



# if __name__ == "__main__":
#     # uvicorn.run("main:app", port=80, reload=False, access_log=False)
#     print("Starting server...")
