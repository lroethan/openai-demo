import os
import pymysql
import psycopg2

class DatabaseConnector:
    def __init__(self, database, host=None, port=None, user=None, password=None):
        self.database = database
        self.host = host or os.getenv('DB_HOST', '')
        self.port = port or int(os.getenv('DB_PORT', 3306))  
        self.user = user or os.getenv('DB_USER', '')
        self.password = password or os.getenv('DB_PASSWORD', '')
        self.connection = None
        self.cursor = None

    def connect(self):
        pass

    def execute(self, query):
        pass

    def fetch_all(self):
        pass
    
    def execute_query(self, query):
        pass
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

class MySQLConnector(DatabaseConnector):
    def connect(self):
        self.connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )
        self.cursor = self.connection.cursor()

    def execute(self, query):
        self.cursor.execute(query)

    def fetch_all(self):
        return self.cursor.fetchall()
    
    def execute_query(self, query):
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result

class PostgreSQLConnector(DatabaseConnector):
    def connect(self):
        self.connection = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )
        self.cursor = self.connection.cursor()

    def execute(self, query):
        self.cursor.execute(query)

    def fetch_all(self):
        return self.cursor.fetchall()
    
    def execute_query(self, query):
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result