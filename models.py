from peewee import Model, CharField, TextField
from database import db
import uuid

class BaseModel(Model):
    class Meta:
        database = db

class Task(BaseModel):
    id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
    input = TextField()
    output = TextField(null=True)
    
# Create the tables
db.connect()
db.drop_tables([Task]) # TODO: peewee-db-evolve
db.create_tables([Task])