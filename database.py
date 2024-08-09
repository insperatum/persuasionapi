import os
from playhouse.db_url import connect, parse
from playhouse.pool import PooledPostgresqlDatabase
from contextlib import contextmanager
from functools import wraps
from peewee import PostgresqlDatabase

db = connect(os.getenv('DATABASE_URL'))

# Parse the DATABASE_URL
# parsed_url = parse(os.getenv('DATABASE_URL'))

# # Create a pooled database instance
# db = PooledPostgresqlDatabase(
#     parsed_url['database'],
#     user=parsed_url['user'],
#     password=parsed_url.get('password', ''),
#     host=parsed_url['host'],
#     port=parsed_url.get('port', 5432),  # Default port for PostgreSQL
#     max_connections=32,
#     stale_timeout=300,  # 5 minutes
# )

# from peewee import DatabaseProxy

# db_proxy = DatabaseProxy()

# def initialize_db():
#     if not db_proxy.obj:
#         db = connect(os.getenv('DATABASE_URL'))
#         db_proxy.initialize(db)
#     return db_proxy

# database_url = os.getenv('DATABASE_URL')
# db = PostgresqlDatabase(None)

# def initialize_db():
#     db.init(database_url)

import functools
from peewee import OperationalError

def with_database(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if db.is_closed():
                db.connect()
            return func(*args, **kwargs)
        except OperationalError as e:
            print(f"Database error: {e}")
            raise
        finally:
            if not db.is_closed():
                db.close()
    return wrapper

def with_async_database(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            if db.is_closed():
                db.connect()
            return await func(*args, **kwargs)
        except OperationalError as e:
            print(f"Database error: {e}")
            raise
        finally:
            if not db.is_closed():
                db.close()
    return wrapper