from fastapi import FastAPI, Request, Response, HTTPException
import requests
import configparser
from fastapi.responses import HTMLResponse, FileResponse
#import scrapers.avanza_scraper as avanza_scraper
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

Config = configparser.ConfigParser()
Config.read('./config.ini')
server_host_address = "localhost:8080" if (Config["MODE"]["development"]) else "backend" 

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="static")

@app.on_event("startup")
async def startup():
    print("starting server....")

    
@app.on_event("shutdown")
async def shutdown():
    print("server shutting down....")
    

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return {"message": "Startpage"}

@app.get("/portfolio")
async def getPortfolio(request: Request):
    res = requests.get(f'http://{server_host_address}/getPortfolio')
    if res.status_code == 200:
        print(res.json())
        content = res.json()
        data = content.get("data")
        columns = content.get("columns")
        return templates.TemplateResponse("template.html", {"request": request, "data": data, "columns": columns})
    else:
        raise(HTTPException(status_code=res.status_code, detail="Error"))
        
@app.get("/portfolio/update")
async def updatePortfolio():
    #avanza_scraper.scrape()
    #return {"message": "Update Portfolio"}
    res = requests.get(f'http://{server_host_address}/doRefresh')
    if res.status_code == 200:
        data = res.json()
        return data
    else:
        raise(HTTPException(status_code=res.status_code, detail="Error"))

@app.get("/portfolio/download")
async def downloadPortfolio():
    #return FileResponse(f'{constants.excelSaveLocation}/portfolio.xlsx', media_type='application/octet-stream',filename="portfolio.xlsx")
    return {"message": "Update Portfolio"}
