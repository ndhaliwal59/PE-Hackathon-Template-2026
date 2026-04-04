from peewee import CharField, DateTimeField, IntegerField

from app.database import BaseModel


class User(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField()
    email = CharField()
    created_at = DateTimeField()

    class Meta:
        table_name = "users"
