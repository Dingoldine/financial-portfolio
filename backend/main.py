from fastapi import FastAPI, Request, Response, Depends, BackgroundTasks 
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Database
from pydantic import BaseModel
from typing import Optional
from multiprocessing import Process
import time, configparser, json
from celery import Celery

Config = configparser.ConfigParser()
Config.read('./config.ini')

if (Config["NETWORK-MODE"]["localhost"] == True):
    celery_broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
    celery_backend = 'redis://localhost:6379/0' 
else:
    celery_broker = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@{Config["CELERY"]["RABBITMQ_HOSTNAME"]}'
    celery_backend = f'redis://{Config["REDIS"]["REDIS_HOSTNAME"]}:6379/0'

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

celeryapp = Celery('portfolio_worker', broker=celery_broker, backend=celery_backend)

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
    except Exception:
        raise


@app.on_event("shutdown")
async def shutdown():
    print("server shutting down...")
    await db.disconnect()

@app.get('/getStatus/{job}')
def getStatus(job):
    print("JOB ID TO CHECK:", job)
    async_result = celeryapp.AsyncResult(job)

    return async_result.state

@app.get("/getQRBinary")
def getQR():
    data = db.fetch_qr_code()
    test = 'data:image/gif;base64,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'
    return {'data': data}

@app.get("/getPortfolio")
def getPortfolio():
    data = db.fetch_portfolio()[0][0]
    performance = db.fetch_portfolio_performance()[0][0]
    return {"data": data, "performance": performance}

@app.get("/getFunds")
def getFunds():
    data = db.fetch_funds()[0][0]
    performance = db.fetch_portfolio_performance("is_fund=TRUE")[0][0]
    return {"data": data, "performance": performance}

@app.get("/getStocks")
def getStocks():
    data = db.fetch_stocks()[0][0] # for some reason the result is way nested
    performance = db.fetch_portfolio_performance("is_fund=FALSE")[0][0]
    return {"data": data, "performance": performance}

@app.get("/doRefresh")
def doRefresh(dbSession: Session = Depends(get_db)):
    async_result = celeryapp.send_task('portfolio_worker.updatePortfolio', args=())
    id_list = async_result.get()
    print(id_list)
    target_id = id_list[0][0]
    return target_id
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
