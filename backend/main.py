from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import constants
from sqlalchemy.orm import Session
from database import Database
from scrapers import avanza_scraper, nasdaq_omx_scraper, event_watcher
from portfolio import Portfolio
from multiprocessing import Process
from helpermodules import valuation
import time


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
#to have our SessionLocal database connection when needed and that the session is closed after use.
def get_db():
    try:
        db_conn = db.getLocalSession()
        yield db_conn
    finally:
        db_conn.close()


@app.on_event("startup")
async def startup():
    print("starting server....")
    global db
    global P
    P = Portfolio()
    db = Database()
    db.connect()
    db.create()
    db.commit()
    
@app.on_event("shutdown")
async def shutdown():
    print("server shutting down...")
    await db.disconnect()





#
#P.checkRules()
#P.updateDatabase()
# #db.reset()
# #db.disconnect()
# data = db.fetch_stocks()
""" def Refresh():
    print("PERFORMING RESET!")
    #fileWatcherProcess = Process(target=event_watcher.startObserver, args=())
    #fileWatcherProcess.start()
    #avanza_scraper.scrape()
    #nasdaq_omx_scraper.scrape()
    #nasdaq_omx_scraper.saveStockInfoToExcel()
    print("Initializing portfolio ...")

    #P.fundsBreakdown()
    #P.stocksBreakdown()

    #valuation.valuation('EQT')
    #fileWatcherProcess.terminate() """



@app.get("/getPortfolio")
async def getPortfolio():
    data = db.fetch_stocks()
    return data

@app.get("/doRefresh")
def doRefresh(dbSession: Session = Depends(get_db)):
    P.stocksBreakdown()
    stocks = P.getStocks()
    db.createTableFromDF(stocks, "stocks")
    result = dbSession.execute("SELECT * FROM stocks")
    return result.fetchall()
    



# if __name__ == "__main__":
#     # uvicorn.run("main:app", port=80, reload=False, access_log=False)
#     print("Starting server...")
