import configparser
import time
from io import StringIO
import psycopg2
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import pool, create_engine, Integer, String, Numeric, Float, Boolean, DateTime, BigInteger, text
#import numpy as np


class Database:

    def __init__(self):
        Config = configparser.ConfigParser()
        Config.read('./config.ini')

        if Config['NETWORK-MODE']['localhost'] == True:
            Config['DATABASE']['host'] = 'localhost'

        self.db_config = dict(Config.items('DATABASE'))

        self.cursor = None
        self.connection = None
        self.engine = None

    def connect(self):
        for attempt in range(10):
            try:
                connection = psycopg2.connect(**self.db_config)

                cursor = connection.cursor()
                # Print TimescaleDB Connection properties
                print(connection.get_dsn_parameters(), "\n")

                # Print TimescaleDB version
                cursor.execute("SELECT version();")
                record = cursor.fetchone()
                print("You are connected to - ", record, "\n")

                self.connection = connection
                self.cursor = cursor
                # SQLALCHEMY ENGINE
                self.engine = create_engine('postgresql+psycopg2://{}:{}@{}/{}'.format(
                    self.db_config["user"], self.db_config["password"], self.db_config["host"], self.db_config["database"]), echo=True, pool_pre_ping=True)
            except (Exception, psycopg2.Error) as error:
                print("Error while connecting to TimescaleDB", error)
                print(f"Retrying in {1 + attempt * attempt}")
                time.sleep(1 + attempt * attempt)
                continue
            else:
                break
        else:
            print("Error while connecting to TimescaleDB, aborting...")
            raise ConnectionError

    def get_local_session(self):
        return sessionmaker(autocommit=False, autoflush=False, bind=self.engine)()

    def create(self):

        sql_commands = (
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL,
                dt DATE NOT NULL,
                asset VARCHAR(255),
                symbol VARCHAR(255),
                shares NUMERIC NOT NULL,
                currency VARCHAR(255),
                market_value_sek NUMERIC NOT NULL,
                purchase_price NUMERIC NOT NULL,
                latest_price NUMERIC NOT NULL,
                change NUMERIC NOT NULL,
                profit NUMERIC NOT NULL,
                weight NUMERIC NOT NULL,
                weight_portfolio NUMERIC NOT NULL,
                is_fund BOOLEAN NOT NULL,
                country VARCHAR(255),
                asset_class VARCHAR(255),
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
                isin VARCHAR(255),
                unlevered_beta_global NUMERIC,
                unlevered_beta_us NUMERIC,
                PRIMARY KEY (asset, dt)
            );
            """,
            """
            CREATE INDEX ON portfolio (asset, dt DESC);
            """,
            """
            SELECT create_hypertable('portfolio', 'dt', if_not_exists => TRUE, migrate_data => TRUE);
            """,
            """ 
            CREATE TABLE IF NOT EXISTS qr_table (
                qr_code TEXT,
                ts TIMESTAMP WITHOUT TIME ZONE,
                PRIMARY KEY (md5(qr_code), ts)
            );
            """
        )
        for query in sql_commands:
            self.query(query)

        self.commit()

    def reset(self):
        query = 'DROP TABLE IF EXISTS "portfolio" CASCADE;'
        self.query(query)
        self.create()

    def store_qr_code(self, binary):
        query = f"""
            INSERT INTO qr_table VALUES ('{str(binary)}', '{pd.Timestamp.now()}');
        """
        self.query(query)
        self.commit()

    def create_table_from_df(self, json, table_name):

        # # drop manually because of bug
        # # see locks query
        # self.query('select pid, usename, pg_blocking_pids(pid) as blocked_by, query as blocked_query from pg_stat_activity where cardinality(pg_blocking_pids(pid)) > 0;')
        # # clear locks query
        # self.query("SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid();")
        # self.query(f'DROP TABLE IF EXISTS {tableName} CASCADE;')
        # self.commit()

        df = pd.read_json(StringIO(json), orient='index')
        df['dt'] = pd.datetime.now().date()
        df['asset_class'] = 'undefined'
        df.columns = df.columns.str.replace(
            ' ', '_').str.lower().str.replace('(', '').str.replace(')', '')
        # df.reset_index(inplace=True)

        #df.rename(columns={ df.columns[0]: 'asset' }, inplace=True)

        def change_type(x):
            switcher = {
                'i': BigInteger(),
                'f': Float(),
                'O': String(),
                'b': Boolean(),
                'M': DateTime()
            }
            return switcher.get(x.kind)

        data_type_dict = dict(df.dtypes.apply(change_type))

        try:
            with self.engine.connect() as connection:
                # fetch previously defined asset classes if exists
                query = "SELECT DISTINCT ON (asset) asset, dt, asset_class FROM portfolio WHERE asset_class != 'undefined' ORDER BY asset, dt DESC;"
                result = connection.execute(query)
                for row in result:
                    df.loc[df['asset'] == row['asset'],
                           'asset_class'] = row['asset_class']

                df.to_sql(table_name, con=connection, index=False,
                          dtype=data_type_dict, if_exists='append')

        except Exception:
            raise

    def disconnect(self):
        try:
            self.cursor.close()
            self.connection.close()
            print("TimescaleDB connection is closed")
        except (Exception, psycopg2.Error) as error:
            print("Error while disconnecting from TimescaleDB", error)

    def query(self, query):
        try:
            print("executing: ", query)
            self.cursor.execute(query)
        except:
            self.connection.rollback()
            raise

    def get_column_names(self, table_name):
        result = []
        self.query(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{}';".format(table_name))
        for col in self.cursor.fetchall():
            result.append(col[0].upper())
        return result

    def update_portfolio_table(self, item, session):
        try:
            command = f"UPDATE portfolio SET asset_class='{item.asset_class}' WHERE asset='{item.asset}';"
            session.execute(text(command))
            session.commit()
        except:
            session.rollback()
            raise

    def fetch_qr_code(self):
        query = """
            SELECT DISTINCT ON (qr_code)
                *
            FROM
                qr_table
            ORDER BY
                qr_code,
                ts DESC;
            """
        self.query(query)
        self.commit()
        result = self.cursor.fetchall()
        return result

    def fetch_stocks(self):
        select_list = "*"
        query = f"""
        SELECT
            coalesce(JSON_AGG(t), NULL)
        FROM ( SELECT DISTINCT ON (asset)
                {select_list}
            FROM
                portfolio
            WHERE is_fund=FALSE
            ORDER BY
                asset,
                dt DESC) AS t; """
        self.query(query)
        self.commit()
        result = self.cursor.fetchall()
        if result[0][0]:
            return result
        else:
            return [[[]]]

    def fetch_funds(self):
        select_list = "*"
        query = f"""
        SELECT
            coalesce(JSON_AGG(t), NULL)
        FROM ( SELECT DISTINCT ON (asset)
                {select_list}
            FROM
                portfolio
            WHERE is_fund=TRUE
            ORDER BY
                asset,
                dt DESC) AS t; """
        self.query(query)
        self.commit()
        result = self.cursor.fetchall()
        if result[0][0]:
            return result
        else:
            return [[[]]]

    def fetch_portfolio(self):
        select_list = "asset, shares, ROUND(cast(purchase_price as numeric),2) AS purchase_price, ROUND(cast(latest_price as numeric),2) AS latest_price, ROUND(cast(market_value_sek as numeric),2) AS market_value_sek, ROUND(cast(change as numeric),4) AS change, currency, isin, symbol, ROUND(cast(weight_portfolio as numeric),4) AS weight, asset_class"
        query = f"""
        SELECT
            coalesce(JSON_AGG(t), NULL)
        FROM ( SELECT DISTINCT ON (asset)
                {select_list}
            FROM
                portfolio
            ORDER BY
                asset,
                dt DESC) AS t; """
        self.query(query)
        self.commit()
        result = self.cursor.fetchall()
        if result[0][0]:
            return result
        else:
            return [[[]]]

    def fetch_portfolio_performance(self, where_condition=None):
        query = """
                SELECT
            coalesce(JSON_AGG(t), NULL)
        FROM (
            SELECT
                asset_class,
                dt,
                SUM(market_value_sek) AS total
            FROM
                portfolio
            GROUP BY
                asset_class,
                dt
            ORDER BY
                dt, total) AS t;
        """
        if where_condition:
            query = f"""
                    SELECT
                coalesce(JSON_AGG(t), NULL)
            FROM (
                SELECT
                    asset_class,
                    dt,
                    SUM(market_value_sek) AS total
                FROM
                    portfolio
                WHERE {where_condition}
                GROUP BY
                    asset_class,
                    dt
                ORDER BY
                    dt, total) AS t;
            """
        self.query(query)
        self.commit()
        result = self.cursor.fetchall()
        if result[0][0]:
            return result
        else:
            return [[[]]]

    def commit(self):
        print("COMMITING: ")
        self.connection.commit()
