from peewee import Model, CharField, IntegerField, UUIDField
from database import db

class BaseModel(Model):
    class Meta:
        database = db
        
class AddResult(BaseModel):
    x = IntegerField()
    y = IntegerField()
    result = IntegerField()

class Request(BaseModel):
    id = UUIDField()
    input = CharField()
    output = CharField()
    
# Create the tables
db.connect()
db.create_tables([AddResult, Request])