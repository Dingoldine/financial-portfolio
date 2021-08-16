from typing import Optional
import configparser
import sys
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Database
from pydantic import BaseModel
from celery import Celery

Config = configparser.ConfigParser()
Config.read('./config.ini')

if Config['NETWORK-MODE']['localhost'] is True:
    CELERY_BROKER = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@localhost'
    CELERY_BACKEND = 'redis://localhost:6379/0'
else:
    CELERY_BROKER = f'pyamqp://{Config["CELERY"]["RABBITMQ_DEFAULT_USER"]}:{Config["CELERY"]["RABBITMQ_DEFAULT_PASS"]}@{Config["CELERY"]["RABBITMQ_HOSTNAME"]}'
    CELERY_BACKEND = f'redis://{Config["REDIS"]["REDIS_HOSTNAME"]}:6379/0'

DB = None
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

celeryapp = Celery('portfolio_worker', broker=CELERY_BROKER,
                   backend=CELERY_BACKEND)

# Dependency: db_conn Generator
# The get_db() function ensures that any route passed this function ought
# to have our SessionLocal database connection when needed and that
# the session is closed after use.
def get_db():
    try:
        db_conn = DB.get_local_session()
        yield db_conn
    finally:
        db_conn.close()

@app.on_event("startup")
async def startup():
    print("starting server....")
    try:
        print('Initializing database connection..')
        global DB
        global P
        DB = Database()
        DB.connect()
        DB.create()
    except Exception:
        sys.exit(-1)

@app.on_event("shutdown")
async def shutdown():
    print("server shutting down...")
    DB.disconnect()


@app.get('/getStatus/{job}')
def get_status(job):
    print("JOB ID TO CHECK:", job)
    async_result = celeryapp.AsyncResult(job)

    return async_result.state

@app.get("/getQRBinary")
def get_qr():
    data = DB.fetch_qr_code()
    return {'data': data}

@app.get("/getPortfolio")
def get_portfolio():
    data = DB.fetch_portfolio()[0][0]
    performance = DB.fetch_portfolio_performance()[0][0]
    return {"data": data, "performance": performance}


@app.get("/getFunds")
def get_funds():
    data = DB.fetch_funds()[0][0]
    performance = DB.fetch_portfolio_performance("is_fund=TRUE")[0][0]
    return {"data": data, "performance": performance}


@app.get("/getStocks")
def get_stocks():
    data = DB.fetch_stocks()[0][0]  # for some reason the result is way nested
    performance = DB.fetch_portfolio_performance("is_fund=FALSE")[0][0]
    return {"data": data, "performance": performance}

class Stock(BaseModel):
    asset: str
    change: float
    currency: str
    isin: str
    latest_price: float
    market_value_sek: float
    purchase_price: float
    weight: float
    shares: float
    symbol: str
    asset_class: Optional[str]
@app.put('/updateStock')
def update_stock(stock: Stock, db_session: Session = Depends(get_db)):
    print(stock)
    DB.update_portfolio_table(stock, db_session)
    return {"message": "update successfull"}

@app.get("/doRefresh")
def do_refresh():
    async_result = celeryapp.send_task(
        'portfolio_worker.updatePortfolio', args=())
    id_list = async_result.get()
    print(id_list)
    target_id = id_list[0][0]
    return target_id

@app.get("/resetDatabase")
def reset_database():
    DB.reset()
    DB.commit()
    return {"message": "reset complete"}
