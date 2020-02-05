import pandas as pd
import os
def printDf(df):
    if(hasattr(df, 'name')):
        print("--------------------------------" + df.name + "--------------------------------")
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
