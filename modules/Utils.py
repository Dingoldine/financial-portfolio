import pandas as pd
import os, xlrd

def printDf(df):
    """Given a dataframe object the functrion pretty prints the frame to the console."""
    if(hasattr(df, 'name')):
        if (df.name):
            print("--------------------------------" + str(df.name) + "--------------------------------")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)

def saveTxtFile(text, filename):
    """Given a filename saves the file the file as a .txt file."""
    savePath = os.path.abspath(os.getcwd()) + "/text_files"
    with open(f'{savePath}/{filename}.txt', 'w') as f:
        f.write(text)

def readTxtFile(filename):
    """Given a filename returns the content as a String."""
    readPath = os.path.abspath(os.getcwd()) + "/text_files"
    with open(f'{readPath}/{filename}.txt','r') as f:
        html = f.read()
    return html


def readExcel(filename):
    """Given a filename returns the excelfile as an XLRD workbook."""
    readPath = os.path.abspath(os.getcwd()) + "/excel_files"
    try:
    # To open Workbook 
        wb = xlrd.open_workbook(f'{readPath}/{filename}') 
    except FileNotFoundError:
        raise(FileNotFoundError)
    return wb
  