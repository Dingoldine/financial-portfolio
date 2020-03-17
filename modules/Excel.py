import pandas as pd
import os
def create(dataframes, filename, index_level=1):
    '''Takes a list of dataframes and creates an excelfile with given filename, index_level should be 1 if the dataframes has column names '''
    saveLocation = os.path.abspath(os.getcwd()) + "/excel_files"
    writer = pd.ExcelWriter(f'{saveLocation}/{filename}.xlsx', engine='xlsxwriter')
    for df in dataframes:
        df.to_excel(writer, df.name)
        # add index widths formatting
        max_index_len = df.index.astype(str).map(len).max() + 1 
        worksheet = writer.sheets[df.name]  # pull worksheet object
        worksheet.set_column(0, 0, max_index_len) # set first row width to 30
        # add formatting, set column widths automatically
        for idx, col in enumerate(df):  # loop through all columns
            series = df[col]
            
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
                )) + 1  # adding a little extra space

            worksheet.set_column(idx + index_level, idx + index_level, max_len)  # set column width
    writer.save()
    print("saved to excel: " + filename)

