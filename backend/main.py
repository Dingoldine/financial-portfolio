from fastapi import FastAPI, Request, Response, Depends, BackgroundTasks 
from fastapi.middleware.cors import CORSMiddleware
import constants
from sqlalchemy.orm import Session
from database import Database
from helpermodules import valuation
import time
from multiprocessing import Process
import time
from celery_worker import updatePortfolio


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
    db = Database()
    db.connect()
    db.create()
    db.commit()
@app.on_event("shutdown")
async def shutdown():
    print("server shutting down....")
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


@app.get("/getFunds")
async def getFunds():
    data = db.fetch_funds()
    columns = db.getColumnNames('funds')
    return {"data": data, "columns": columns}

@app.get("/getStocks")
async def getStocks():
    data = db.fetch_stocks()
    columns = db.getColumnNames('stocks')
    return {"data": data, "columns": columns}

@app.get("/doRefresh")



# I'm using fastAPI exactly like this, combining concurrent.futures.ProcessPoolExecutor() and asyncio to manage long running jobs.

# If you don't want to rely on other modules (celery etc), you need to manage yourself the state of your job, and store it somewhere. I store it in the DB so that pending jobs can be resumed after a restart of the server.

# Note that you must NOT perform CPU intensive computations in the background_tasks of the app, because it runs in the same async event loop that serves the requests and it will stall your app. Instead submit them to a thread pool or a process pool.

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
    res = updatePortfolio.delay()
    #print(res.status) # 'SUCCESS'
    #print(res.id) # '432890aa-4f02-437d-aaca-1999b70efe8d'
    return {"message": "update request received"}

def __test():
    print("starting task")
    time.sleep(10)
    print("complete")
@app.get("/testMulti")
def testMulti():
    # fileWatcherProcess = Process(target=__test, args=())
    # fileWatcherProcess.start()
    # fileWatcherProcess.terminate()
    #background_tasks.add_task(__test)

    res = add.delay(1, 2)

    return {'message': res}

@app.get("/resetDatabase")
def resetDatabase():
    db.reset()
    db.commit()
    return {"message": "reset complete"}



# if __name__ == "__main__":
#     # uvicorn.run("main:app", port=80, reload=False, access_log=False)
#     print("Starting server...")
