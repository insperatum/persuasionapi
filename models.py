from peewee import Model, CharField, TextField, ForeignKeyField, FloatField
from database import db
import uuid

class BaseModel(Model):
    class Meta:
        database = db

class Task(BaseModel):
    id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
    input = TextField()
    output = TextField(null=True)

class Message(BaseModel):
    id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
    source = CharField() #"USER" or "BOT"
    value = TextField()

class Prediction(BaseModel):
    id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
    model = CharField()
    message = ForeignKeyField(Message, backref='predictions')
    value = FloatField

# Create the tables
db.connect()
db.drop_tables([Task, Message, Prediction]) # TODO: peewee-db-evolve
db.create_tables([Task, Message, Prediction])