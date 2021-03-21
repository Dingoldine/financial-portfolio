import configparser, psycopg2, sys, time

#from io import StringIO
import pandas as pd
from io import StringIO
from sqlalchemy.orm import sessionmaker
from sqlalchemy import pool, create_engine, Integer, String, Numeric, Float, Boolean, DateTime, BigInteger
from helpermodules import Utils
#import numpy as np
class Database:

    def __init__(self):
        Config = configparser.ConfigParser()
        Config.read('./config.ini')
        
        if (Config["NETWORK-MODE"]["localhost"] == True):
            Config["DATABASE"]["host"] = "localhost"

        self.dbConfig = dict(Config.items("DATABASE"))


    def connect(self):
        for attempt in range(10):
            try:
                connection = psycopg2.connect(**self.dbConfig)

                cursor = connection.cursor()
                # Print PostgreSQL Connection properties
                print ( connection.get_dsn_parameters(),"\n")

                # Print PostgreSQL version
                cursor.execute("SELECT version();")
                record = cursor.fetchone()
                print("You are connected to - ", record,"\n")

                self.connection = connection
                self.cursor = cursor
                
                ## SQLALCHEMY ENGINE-
                self.engine = create_engine('postgresql+psycopg2://{}:{}@{}/{}'.format(self.dbConfig["user"], self.dbConfig["password"],self.dbConfig["host"], self.dbConfig["database"]), echo=True, pool_pre_ping=True)
            except (Exception, psycopg2.Error) as error :
                print("Error while connecting to PostgreSQL", error)
                print("Retrying in: ", 1 + attempt * attempt)
                time.sleep(1 + attempt * attempt)
                continue
            else:
                break
        else:
            print("Error while connecting to PostgreSQL", error)
    def getLocalSession(self):
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        return SessionLocal()

    def create(self):
        # problem inserting numeric missing data values as with the stringIO stream we can not insert NULL,
        # pandas treat missing values an ""
        sql_commands = (
        """
        CREATE TABLE IF NOT EXISTS stocks (
            id SERIAL PRIMARY KEY,
            asset VARCHAR(255) UNIQUE NOT NULL,
            amount NUMERIC NOT NULL,
            purchase NUMERIC NOT NULL,
            market_value NUMERIC NOT NULL,
            change NUMERIC NOT NULL,
            profit NUMERIC NOT NULL,
            weight NUMERIC NOT NULL,
            ticker VARCHAR(255),
            country VARCHAR(255),
            broad_region VARCHAR(255),
            sub_region VARCHAR(255),
            industry_group_damodaran VARCHAR(255),
            sector_morningstar VARCHAR(255),
            industry_morningstar VARCHAR(255),
            stock_style_morningstar VARCHAR(255),
            fiscal_year_ends VARCHAR(255),
            employees NUMERIC(7),
            website VARCHAR(255),
            eps_2019 NUMERIC,
            unlevered_beta_global NUMERIC,
            unlevered_beta_us NUMERIC
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS funds (
            id SERIAL PRIMARY KEY,
            asset VARCHAR(255) UNIQUE NOT NULL,
            amount NUMERIC NOT NULL,
            purchase NUMERIC NOT NULL,
            market_value NUMERIC NOT NULL,
            change NUMERIC NOT NULL,
            profit NUMERIC NOT NULL
        )
        """)
        for command in sql_commands:
            self.query(command)

    def reset(self):
        sql_commands = (
        'DROP TABLE IF EXISTS "stocks" CASCADE;',
        'DROP TABLE IF EXISTS "funds" CASCADE;',
        )
        for command in sql_commands:
            self.query(command)

        self.create()

    
    # HAS PROVEN TO CAUSE LOCKS ON DATABASE IF TABLE ALREADY EXISTS
    def createTableFromDF(self, json, tableName):
        # drop manually because of bug 

        # see locks query
        self.query('select pid, usename, pg_blocking_pids(pid) as blocked_by, query as blocked_query from pg_stat_activity where cardinality(pg_blocking_pids(pid)) > 0;')
        # clear locks query
        self.query('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid();')
        self.query(f'DROP TABLE IF EXISTS {tableName} CASCADE;')
        self.commit()


        df=pd.read_json(StringIO(json), orient='index')
        print(df.head(5))
        #df = df.copy()
        df.columns = df.columns.str.replace(' ', '_').str.lower().str.replace('(', '').str.replace(')', '')
        df.reset_index(inplace=True)

        df.rename(columns={ df.columns[0]: 'asset' }, inplace=True)

        def changeType(x):
            switcher = {
                'i': BigInteger(),
                'f': Float(),
                'O': String(),
                'b': Boolean(),
                'M': DateTime()
            }
            return switcher.get(x.kind)
 
        dTypeDict = dict(df.dtypes.apply(changeType))

        try:
            with self.engine.connect() as connection:
                df.to_sql(tableName, con=connection, index=False, dtype=dTypeDict, if_exists='replace')
            
            # print(self.engine.execute(f'SELECT * FROM {tableName}').fetchall())
        
        except Exception as e:
            raise(e)
        """      
        # create a copy
        name = df.name 
        df = df.copy()
        df.reset_index(inplace=True)
        # Initialize a string buffer
        sio = StringIO()
        sio.write(df.to_csv(index=False, header=None, na_rep=None))  # Write the Pandas DataFrame as a csv to the buffer
        sio.seek(0)  # Be sure to reset the position to the start of the stream
        # Copy the string buffer to the database, as if it were an actual file

        sql_safe_columns = df.columns.str.replace(' ', '_').str.lower().str.replace('(', '').str.replace(')', '')


        print(list(sql_safe_columns))
        try:
            with self.cursor as c:
                c.copy_from(sio, name, columns=sql_safe_columns, sep=',')
                self.commit()
        except (Exception, psycopg2.Error) as error:
            print ("Error while updating database table from pandas dataframe".upper(), error) 
        """
    def disconnect(self):
        try: 
            self.cursor.close()
            self.connection.close()
            print("PostgreSQL connection is closed")
        except (Exception, psycopg2.Error) as error :
            print ("Error while disconnecting from PostgreSQL", error)
            
    def query(self, query):
        try:  
            print("executing: ", query)
            self.cursor.execute(query)
            print(self.cursor.fetchall())
        except psycopg2.ProgrammingError:
            pass
    def getColumnNames(self, tableName):
        # self.cursor.execute("SELECT current_schema();")
        # self.cursor.execute("SELECT * FROM stocks;")
        result = []
        self.cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{}';".format(tableName))
        for col in self.cursor.fetchall():
            result.append(col[0].upper())
        return result

    def fetch_stocks(self):
        try:
            self.cursor.execute("SELECT * FROM stocks")
            return self.cursor.fetchall()
        except psycopg2.InterfaceError as e:
            print(e)
            self.disconnect()
            self.connect()
    def fetch_funds(self):
        try:
            self.cursor.execute("SELECT * FROM funds")
            return self.cursor.fetchall()
        except psycopg2.InterfaceError as e:
            print(e)
            self.disconnect()
            self.connect()

    def commit(self):
        print("COMMITING: ")
        self.connection.commit()