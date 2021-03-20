import pandas as pd
import os, xlrd
from openpyxl import load_workbook
import constants
import logging

def printDf(df):
    """Given a dataframe object the functrion pretty prints the frame to the console."""
    if(hasattr(df, 'name')):
        if (df.name):
            print("--------------------------------" + str(df.name) + "--------------------------------")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)

def saveTxtFile(text, filename):
    """Given a filename saves the file the file as a .txt file."""

    with open(f'{constants.txtSaveLocation}/{filename.replace(" ", "")}.txt'.encode('ascii',errors='ignore').decode(), 'w') as f:
        f.write(text)

def readTxtFile(filename):
    """Given a filename returns the content as a String."""
    
    with open(f'{constants.txtSaveLocation}/{filename.replace(" ", "")}.txt'.encode('ascii',errors='ignore').decode(),'r') as f:
        content = f.read()
    return content


def readExcel(filename):
    """Given a filename returns the excelfile as an XLRD workbook."""
    try:
        # To open Workbook 
        wb = xlrd.open_workbook(f'{constants.excelSaveLocation}/{filename}') 

        return wb

    except FileNotFoundError:
        raise
    
def readXLSX():
    pass

def log_error(e):
    """
    It is always a good idea to log errors. 
    This function just prints them, but you can
    make it do anything.
    """
    logging.exception("message")