import os
from playhouse.db_url import connect

db = connect(os.getenv('DATABASE_URL'))