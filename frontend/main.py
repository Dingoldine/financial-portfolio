from fastapi import FastAPI, Request
import requests
from fastapi.responses import HTMLResponse, FileResponse
#import scrapers.avanza_scraper as avanza_scraper
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates



app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return {"message": "Startpage"}



@app.get("/portfolio")
async def getPortfolio(request: Request):
    res = requests.get('http://backend/getPortfolio')
    if res.status_code == 200:
        data = res.json().data
        return templates.TemplateResponse("template.html", {"request": request, "data": data})

@app.get("/portfolio/update")
async def updatePortfolio():
    #avanza_scraper.scrape()
    return {"message": "Update Portfolio"}

@app.get("/portfolio/download")
async def downloadPortfolio():
    #return FileResponse(f'{constants.excelSaveLocation}/portfolio.xlsx', media_type='application/octet-stream',filename="portfolio.xlsx")
    return {"message": "Update Portfolio"}
