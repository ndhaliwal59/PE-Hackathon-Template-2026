from flask import Blueprint, jsonify
from peewee import DoesNotExist
from playhouse.shortcuts import model_to_dict

from app.models.url import Url
from app.models.user import User

users_bp = Blueprint("users", __name__)


@users_bp.get("/users")
def list_users():
    users = User.select().order_by(User.id)
    return jsonify([model_to_dict(u, recurse=False) for u in users])


@users_bp.get("/users/<int:user_id>")
def get_user(user_id: int):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404
    return jsonify(model_to_dict(user, recurse=False))


@users_bp.get("/users/<int:user_id>/urls")
def list_user_urls(user_id: int):
    try:
        User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404
    urls = Url.select().where(Url.user_id == user_id).order_by(Url.id)
    return jsonify([model_to_dict(u, recurse=False) for u in urls])
