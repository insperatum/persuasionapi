from peewee import Model, CharField, IntegerField
from database import db

class BaseModel(Model):
    class Meta:
        database = db

# class User(BaseModel):
#     name = CharField()
#     age = IntegerField()

class AddResult(BaseModel):
    x = IntegerField()
    y = IntegerField()
    result = IntegerField()

# Create the tables
db.connect()
db.create_tables([AddResult])