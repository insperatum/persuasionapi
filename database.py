import os
from playhouse.db_url import connect, parse
from playhouse.pool import PooledPostgresqlDatabase

# db = connect(os.getenv('DATABASE_URL'))

# Parse the DATABASE_URL
parsed_url = parse(os.getenv('DATABASE_URL'))

# Create a pooled database instance
db = PooledPostgresqlDatabase(
    parsed_url['database'],
    user=parsed_url['user'],
    password=parsed_url.get('password', ''),
    host=parsed_url['host'],
    port=parsed_url.get('port', 5432),  # Default port for PostgreSQL
    max_connections=32,
    stale_timeout=300,  # 5 minutes
)
