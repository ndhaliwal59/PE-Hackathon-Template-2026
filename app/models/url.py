from peewee import BooleanField, CharField, DateTimeField, ForeignKeyField, IntegerField, TextField

from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User, field="id", backref="urls")
    short_code = CharField()
    original_url = TextField()
    title = CharField()
    is_active = BooleanField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        table_name = "urls"
