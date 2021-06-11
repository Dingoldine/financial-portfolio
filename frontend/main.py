from typing import Optional
import json
import configparser
import requests
from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

Config = configparser.ConfigParser()
Config.read('./config.ini')
SERVER_HOST_ADDRESS = "localhost:8080" if Config['NETWORK-MODE']['localhost'] is True else 'backend'

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="static")


@app.on_event("startup")
def startup():
    print("starting server....")


@app.on_event("shutdown")
def shutdown():
    print("server shutting down....")


@app.get("/")
def root(response_model: RedirectResponse):
    return RedirectResponse("/portfolio")


@app.get("/portfolio")
def get_portfolio(request: Request, response_model: HTMLResponse):
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
def get_stocks(request: Request):
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
    purchase_price: float
    weight: float
    shares: int
    symbol: str
    asset_class: Optional[str]
@app.put("/portfolio/update")
def update_stock(stock: Stock, response_model=Stock):
    print(stock.dict())
    res = requests.put(
        f'http://{SERVER_HOST_ADDRESS}/updateStock', json=stock.dict())
    if (res.status_code) == 200:
        content = res.json()
        msg = content.get("message")
        print(msg)
        return stock.dict()
    else:
        print(res.json())
        raise HTTPException(status_code=res.status_code, detail="Error")

@app.get("/real-estate")
def get_real_estate(request: Request):
    return templates.TemplateResponse("/real_estate_page/real_estate.html", {"request": request})

@app.get("/funds")
def get_funds(request: Request):
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
def update_portfolio(request: Request):
    res = requests.get(f'http://{SERVER_HOST_ADDRESS}/doRefresh')
    if res.status_code == 200:
        data = res.json()
        print(data)
        return templates.TemplateResponse("/update_page/update.html", {"request": request, "id": data})
    else:
        raise HTTPException(status_code=res.status_code, detail="Error")

@app.get("/portfolio/update/success")
def update_portfolio_success(request: Request):
    return templates.TemplateResponse("/success/success.html", {"request": request})

@app.get("/portfolio/update/failure")
def update_portfolio_failure(request: Request):
    return templates.TemplateResponse("/failure/failure.html", {"request": request})


@app.get("/subscribe/qr")
def subscribe_qr(request: Request):
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