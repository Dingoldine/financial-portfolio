from fastapi import FastAPI, Request
import constants
from database import Database

from fastapi.responses import HTMLResponse, FileResponse
import scrapers.avanza_scraper as avanza_scraper
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


db = Database()
db.connect()
#db.reset()
#db.disconnect()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
data = db.fetch_stocks()

templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    print(data)
    return templates.TemplateResponse("template.html", {"request": request, "data": data})

@app.get("/portfolio")
async def getPortfolio():
    return {"message": "Portfolio"}

@app.get("/portfolio/update")
async def updatePortfolio():
    avanza_scraper.scrape()

@app.get("/portfolio/download")
async def downloadPortfolio():
    return FileResponse(f'{constants.excelSaveLocation}/portfolio.xlsx', media_type='application/octet-stream',filename="portfolio.xlsx")

