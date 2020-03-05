import pandas as pd
import os, xlrd
def printDf(df):
    if(hasattr(df, 'name')):
        if (df.name):
            print("--------------------------------" + str(df.name) + "--------------------------------")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)

def saveTxtFile(text, filename):
    savePath = os.path.abspath(os.getcwd()) + "/text_files"
    with open(f'{savePath}/{filename}.txt', 'w') as f:
        f.write(text)

def readTxtFile(filename):
    readPath = os.path.abspath(os.getcwd()) + "/text_files"
    with open(f'{readPath}/{filename}.txt','r') as f:
        html = f.read()
    return html

def readExcel(filename):
    readPath = os.path.abspath(os.getcwd()) + "/excel_files"
    # To open Workbook 
    wb = xlrd.open_workbook(f'{readPath}/{filename}.xlsx') 
    return wb
  