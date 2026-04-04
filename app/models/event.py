from peewee import CharField, DateTimeField, ForeignKeyField, IntegerField, TextField

from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    id = IntegerField(primary_key=True)
    url = ForeignKeyField(Url, field="id", backref="events")
    user = ForeignKeyField(User, field="id", backref="user_events")
    event_type = CharField()
    occurred_at = DateTimeField(column_name="timestamp")
    details = TextField()

    class Meta:
        table_name = "events"
