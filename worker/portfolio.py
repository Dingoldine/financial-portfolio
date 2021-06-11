import numpy as np
import pandas as pd
from io import StringIO 
from helpermodules import Excel
class Portfolio:
    def __init__(self, avanza_holdings, degiro_holdings):
        
        avanza_stocks = pd.read_json(StringIO(avanza_holdings.get("Stocks", pd.DataFrame(columns=[]).to_json())), orient='index')
        funds = pd.read_json(StringIO(avanza_holdings.get("Funds", pd.DataFrame(columns=[]).to_json())), orient='index')
        etfs = pd.read_json(StringIO(avanza_holdings.get("ETFs", pd.DataFrame(columns=[]).to_json())),orient='index')
        self.certificates = pd.read_json(StringIO(avanza_holdings.get("Certificates",  pd.DataFrame(columns=[]).to_json())), orient='index')
        self.summary = pd.read_json(StringIO(avanza_holdings.get("Potfolio Summary",  pd.DataFrame(columns=[]).to_json())), orient='index')

        # formating degiro frame
        degiro_stocks = pd.DataFrame.from_dict(degiro_holdings, orient='index')
        degiro_stocks = degiro_stocks[degiro_stocks["productType"] == "STOCK"]
        degiro_stocks.drop("productType", axis=1, inplace=True)
        degiro_stocks.loc[degiro_stocks["name"].isna(), 'name'] = degiro_stocks['id']
        degiro_stocks.drop('id', axis=1, inplace=True)
        degiro_stocks.columns = degiro_stocks.columns.str.capitalize()
        col_dict = {'Breakevenprice': 'Purchase Price','Size': 'Shares', 'Name': 'Asset', 'Value': 'Market Value (SEK)', 'Price': 'Latest Price'}   ## key→old name, value→new name
        degiro_stocks.columns = [col_dict.get(x, x) for x in degiro_stocks.columns]
        degiro_stocks['Change'] = (degiro_stocks['Latest Price'] / degiro_stocks['Purchase Price'] - 1)
        degiro_stocks['Profit'] = degiro_stocks['Market Value (SEK)'] * degiro_stocks['Change'] - 1
        degiro_stocks.reset_index(inplace=True, drop=True)
        
        # format change column
        avanza_stocks['Change'] = avanza_stocks['Change']/100
        funds['Change'] = funds['Change']/100
        if not etfs.empty:
            etfs['Change'] = etfs['Change']/100
        if not self.certificates.empty:
            self.cert_value = self.certificates['Market Value (SEK)'].sum()
            self.certificates['Weight'] = self.certificates['Market Value (SEK)'] /  self.cert_value
            self.certificates['Change'] = self.certificates['Change']/100
            assert(np.isclose(self.certificates['Weight'].sum(), 1, rtol=1e-03, atol=1e-04))
        else:
            self.cert_value = 0


        # create stock frame
        stock_frames = [avanza_stocks, degiro_stocks]
        self.stocks = pd.concat(stock_frames, ignore_index=True)
        self.stocks.name = "Stocks"
        

        # merge ETFs and Funds
        frames = [funds, etfs]
        concat_funds = pd.concat(frames, keys=['Funds', 'ETFs'])
        self.funds = concat_funds


        self.stocks_value = self.stocks['Market Value (SEK)'].sum()   
        self.funds_value = self.funds['Market Value (SEK)'].sum()
        
        self.stocks['Weight'] = self.stocks['Market Value (SEK)'] /  self.stocks_value
        self.funds['Weight'] = self.funds['Market Value (SEK)'] /  self.funds_value

        assert(np.isclose(self.stocks["Weight"].sum(), 1, rtol=1e-03, atol=1e-04))
        assert(np.isclose(self.funds['Weight'].sum(), 1, rtol=1e-03, atol=1e-04))
 

        self.certificates["is_fund"] = True
        self.funds["is_fund"] = True
        self.stocks["is_fund"] = False

        self.portfolio_value = self.stocks_value + self.funds_value + self.cert_value
        self.portfolio = pd.concat([self.stocks, self.funds, self.certificates], ignore_index=True)
        self.portfolio['Weight_Portfolio'] = self.portfolio['Market Value (SEK)'] /  self.portfolio_value
        self.portfolio.name = "Portfolio"

    def getStocks(self):
        return self.stocks
    def getFunds(self):
        return self.funds
    def getPortfolio(self):
        return self.portfolio
    def generateStocksExcel(self):
        Excel.create([self.stocks], "Stocks", 1)