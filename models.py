from peewee import Model, CharField, TextField, ForeignKeyField, FloatField, BlobField
from database import db
import uuid
import pydantic
import json

class BaseModel(Model):
    class Meta:
        database = db

class JSONField(TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)
        
class Job(BaseModel):
    id = CharField(default=lambda: uuid.uuid4().hex, primary_key=True)
    command = CharField()

    input = JSONField(null=True)
    output = JSONField(null=True)

    progress = FloatField(default=lambda: 0.0)

        
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
# db.drop_tables([Task])#, Message, Prediction]) # TODO: peewee-db-evolve
db.create_tables([Task, Job])#, Message, Prediction])