import numpy as np
import pandas as pd
from helpermodules import Excel

class Portfolio:

    def __init__(self, avanza_holdings, degiro_holdings):

        col_dict = {'Breakevenprice': 'Purchase Price', 'Size': 'Shares', 'Name': 'Asset', 
        'Value': 'Market Value (SEK)', 'Price': 'Latest Price'}  # key→old name, value→new name

        # formating avanza frame(s)
        avanza_frame = pd.DataFrame.from_dict(avanza_holdings, orient='index')
        avanza_frame.columns = avanza_frame.columns.str.capitalize()
        avanza_frame.columns = [col_dict.get(x, x) for x in avanza_frame.columns]
        avanza_frame['Change'] = (avanza_frame['Market Value (SEK)']/avanza_frame['Acquired_value']) - 1 
        avanza_frame.drop("Acquired_value", axis=1, inplace=True)
        avanza_frame['Purchase Price'] = avanza_frame['Latest Price'] /  avanza_frame['Change']
        avanza_frame['Profit'] = avanza_frame['Market Value (SEK)'] * avanza_frame['Change'] - 1

        avanza_stocks = avanza_frame[avanza_frame["Type"] == "STOCK"]
        avanza_stocks.drop("Type", axis=1, inplace=True)

        avanza_certificates = avanza_frame[avanza_frame["Type"] == "CERTIFICATE"]
        avanza_certificates.drop("Type", axis=1, inplace=True)

        avanza_etfs = avanza_frame[avanza_frame["Type"] == "ETF"]
        avanza_etfs.drop("Type", axis=1, inplace=True)

        avanza_funds = avanza_frame[avanza_frame["Type"] == "FUND"]
        avanza_funds.drop("Type", axis=1, inplace=True)

        avanza_cash = avanza_frame[avanza_frame["Type"] == "CASH"]
        avanza_cash.drop("Type", axis=1, inplace=True)

        # formating degiro frame
        degiro_frame = pd.DataFrame.from_dict(degiro_holdings, orient='index')

        degiro_stocks = degiro_frame[degiro_frame["productType"] == "STOCK"]
        degiro_stocks.drop("productType", axis=1, inplace=True)
        degiro_stocks.loc[degiro_stocks["name"].isna(), 'name'] = degiro_stocks['id']
        degiro_stocks.drop('id', axis=1, inplace=True)
        degiro_stocks.columns = degiro_stocks.columns.str.capitalize()
        degiro_stocks.columns = [col_dict.get(x, x) for x in degiro_stocks.columns]
        degiro_stocks.loc[:, 'Change'] = (degiro_stocks['Latest Price'] / degiro_stocks['Purchase Price'] - 1)
        degiro_stocks.loc[:, 'Profit'] = degiro_stocks['Market Value (SEK)'] * degiro_stocks['Change'] - 1
        degiro_stocks.reset_index(inplace=True, drop=True)

        # create stocks frame
        stock_frames = [avanza_stocks, degiro_stocks]
        self.stocks = pd.concat(stock_frames, ignore_index=True)
        self.stocks.name = "Stocks"

        # create funds frame (merge ETFs and Funds)
        frames = [avanza_funds, avanza_etfs]
        concat_funds = pd.concat(frames, keys=['Funds', 'ETFs'])
        self.funds = concat_funds

        self.stocks_value = self.stocks['Market Value (SEK)'].sum()
        self.funds_value = self.funds['Market Value (SEK)'].sum()

        self.stocks['Weight'] = self.stocks['Market Value (SEK)'] / self.stocks_value
        self.funds['Weight'] = self.funds['Market Value (SEK)'] / self.funds_value
        
        # create certificates frames
        self.certificates = avanza_certificates

        if not self.certificates.empty:
            self.cert_value = self.certificates['Market Value (SEK)'].sum()
            self.certificates['Weight'] = self.certificates['Market Value (SEK)'] / self.cert_value
            assert(np.isclose(self.certificates['Weight'].sum(), 1, rtol=1e-03, atol=1e-04))
        else:
            self.cert_value = 0

        assert(np.isclose(self.stocks["Weight"].sum(), 1, rtol=1e-03, atol=1e-04))
        assert(np.isclose(self.funds['Weight'].sum(), 1, rtol=1e-03, atol=1e-04))

        # create cash frame
        self.cash = avanza_cash
        if not self.cash.empty:
            self.cash_value =  self.cash['Market Value (SEK)'].sum()
            self.cash['Weight'] = self.cash['Market Value (SEK)'] / self.cash_value
            self.cash['Symbol'] = '$£KR'
        else:
            self.cash_value = 0 

        self.certificates["is_fund"] = True
        self.funds["is_fund"] = True
        self.stocks["is_fund"] = False
        self.cash["is_fund"] = False

        self.portfolio_value = self.stocks_value + self.funds_value + self.cert_value + self.cash_value
        self.portfolio = pd.concat([self.stocks, self.funds, self.certificates, self.cash], ignore_index=True)
        self.portfolio['Weight_Portfolio'] = self.portfolio['Market Value (SEK)'] / self.portfolio_value
        self.portfolio.name = "Portfolio"

        assert(np.isclose(self.portfolio['Weight_Portfolio'].sum(), 1, rtol=1e-03, atol=1e-04))

    def getStocks(self):
        return self.stocks

    def getFunds(self):
        return self.funds

    def getPortfolio(self):
        return self.portfolio

    def generateStocksExcel(self):
        Excel.create([self.stocks], "Stocks", 1)