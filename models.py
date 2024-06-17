from peewee import Model, CharField, TextField, ForeignKeyField, FloatField, BlobField
from database import db
import uuid
import pydantic

class BaseModel(Model):
    class Meta:
        database = db

class Task(BaseModel):
    id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
    command = CharField()
    model = CharField()
    input = TextField(null=True)
    file = BlobField(null=True)

    question = TextField()
    lower = TextField()
    upper = TextField()
    audience = TextField(default = lambda: "us-adults")
    
    output = TextField(null=True)

    progress = FloatField(default=lambda: 0.0)

# class Message(BaseModel):
#     id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
#     source = CharField() #"USER" or "BOT"
#     value = TextField()

# class Prediction(BaseModel):
#     id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
#     model = CharField()
#     message = ForeignKeyField(Message, backref='predictions')

#     question = TextField()
#     lower = TextField()
#     upper = TextField()
#     audience = TextField()

#     value = FloatField

# Create the tables
db.connect()
db.drop_tables([Task])#, Message, Prediction]) # TODO: peewee-db-evolve
db.create_tables([Task])#, Message, Prediction])