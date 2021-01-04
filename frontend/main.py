from fastapi import FastAPI, Request, Response, HTTPException
import requests
import configparser
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
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
    return RedirectResponse("/portfolio")

@app.get("/portfolio")
async def getPortfolio(request: Request, response_class=HTMLResponse):
    res1 = requests.get(f'http://{server_host_address}/getStocks')
    res2 = requests.get(f'http://{server_host_address}/getFunds')
    
    if (res1.status_code and res2.status_code) == 200:
        content1 = res1.json()
        stock_data = content1.get("data")
        stock_columns = content1.get("columns")

        content2 = res2.json()
        fund_data = content2.get("data")
        fund_columns = content2.get("columns")
        return templates.TemplateResponse("/home_page/home.html", {"request": request, "stock_data": stock_data, "stock_columns": stock_columns,"fund_data": fund_data, "fund_columns": fund_columns})
    else:
        raise(HTTPException(status_code=res1.status_code, detail="Error"))


@app.get("/stocks")
async def getStocks(request: Request, response_class=HTMLResponse):
    res = requests.get(f'http://{server_host_address}/getStocks')
    
    if (res.status_code) == 200:
        content = res.json()
        stock_data = content.get("data")
        stock_columns = content.get("columns")
        return templates.TemplateResponse("/stock_page/stocks.html", {"request": request, "stock_data": stock_data, "stock_columns": stock_columns})
    else:
        raise(HTTPException(status_code=res.status_code, detail="Error"))
        
@app.get("/funds")
async def getFunds(request: Request, response_class=HTMLResponse):
    res = requests.get(f'http://{server_host_address}/getFunds')
    
    if (res.status_code) == 200:
        content = res.json()
        fund_data = content.get("data")
        fund_columns = content.get("columns")
        return templates.TemplateResponse("/funds_page/funds.html", {"request": request, "fund_data": fund_data, "fund_columns": fund_columns})
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
