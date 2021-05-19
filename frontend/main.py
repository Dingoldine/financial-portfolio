from typing import Optional
import json
import configparser
import requests
from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
#import scrapers.avanza_scraper as avanza_scraper
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

Config = configparser.ConfigParser()
Config.read('./config.ini')
SERVER_HOST_ADDRESS = "localhost:8080" if Config['NETWORK-MODE']['localhost'] is True else 'backend'

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
async def get_portfolio(request: Request, response_class=HTMLResponse):
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/getPortfolio')

    if res.status_code == 200:
        content = res.json()
        portfolio_data = content.get("data")
        portfolio_performance = content.get("performance")
        if len(portfolio_data) != 0:
            print(portfolio_data)
            portfolio_headers = list(portfolio_data[0].keys())
        else:
            portfolio_headers = []
        return templates.TemplateResponse("/home_page/home.html", {"request": request, "portfolio_data": portfolio_data, "portfolio_headers": portfolio_headers, "portfolio_performance": portfolio_performance})
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")


@app.get("/stocks")
async def get_stocks(request: Request, response_class=HTMLResponse):
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/getStocks')

    if (res.status_code) == 200:
        content = res.json()
        stock_data = content.get("data")
        stock_performance = content.get("performance")
        print(json.dumps(stock_data, indent=2))
        if len(stock_data) != 0:
            stock_headers = list(stock_data[0].keys())
        else:
            stock_headers = []
        return templates.TemplateResponse("/stock_page/stocks.html", {"request": request, "stock_data": stock_data, "stock_headers": stock_headers, "stock_performance": stock_performance})
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")


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


@app.put("/portfolio/update")
async def update_stock(stock: Stock, response_model=Stock):
    print(stock.dict())
    res = requests.put(
        f'http://{SERVER_HOST_ADDRESS}/updateStock', json=stock.dict())
    if (res.status_code) == 200:
        content = res.json()
        msg = content.get("message")
        print(msg)
        return stock
    else:
        print(res.json())
        raise HTTPException(status_code=res.status_code, detail="Error")

    # res = requests.get(f'http://{SERVER_HOST_ADDRESS}/getStocks')

    # if (res.status_code) == 200:
    #     content = res.json()
    #     stock_data = content.get("data")
    #     print(json.dumps(stock_data, indent=2))
    #     return templates.TemplateResponse("/stock_page/stocks.html", {"request": request, "stock_data": stock_data})
    # else:
    #     raise(HTTPException(status_code=res.status_code, detail="Error"))


@app.get("/funds")
async def get_funds(request: Request, response_class=HTMLResponse):
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/getFunds')

    if (res.status_code) == 200:
        content = res.json()
        fund_data = content.get("data")
        fund_performance = content.get("performance")
        print(json.dumps(fund_data, indent=2))
        if len(fund_data) != 0:
            fund_headers = list(fund_data[0].keys())
        else:
            fund_headers = []
        return templates.TemplateResponse("/funds_page/funds.html", {"request": request, "fund_data": fund_data, "fund_headers": fund_headers, "fund_performance": fund_performance})
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")

@app.get("/portfolio/update")
def update_portfolio(request: Request, response_class=HTMLResponse):
    # avanza_scraper.scrape()
    # return {"message": "Update Portfolio"}
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/doRefresh')
    if res.status_code == 200:
        data = res.json()
        print(data)
        return templates.TemplateResponse("/update_page/update.html", {"request": request, "id": data})
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")


@app.get("/subscribe/qr")
def subscribe_qr():
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/getQRBinary')
    if res.status_code == 200:
        data = res.json()
        print(data)
        return data
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")

@app.get("/subscribe/{job}")
def subscribe(job):
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/getStatus/{job}')
    if res.status_code == 200:
        data = res.json()
        print(data)
        return data
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")

@app.get("/portfolio/download")
def download_portfolio():
    # return FileResponse(f'{constants.excelSaveLocation}/portfolio.xlsx', media_type='application/octet-stream',filename="portfolio.xlsx")
    return {"message": "Update Portfolio"}
