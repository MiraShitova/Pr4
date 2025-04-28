from flask import Flask, request
from flask_restful import Api, Resource
from marshmallow import Schema, fields
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)

class ItemModel(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float(precision=2), unique=False, nullable=False)
    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id"), unique=False, nullable=False
    )
    store = db.relationship("StoreModel", back_populates="items")

    tags = db.relationship("TagModel", back_populates="items", secondary="items_tags")

class StoreModel(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    items = db.relationship("ItemModel", back_populates="store", lazy="dynamic")
    tags = db.relationship("TagModel", back_populates="store", lazy="dynamic")

from marshmallow import Schema, fields

class TagModel(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    store = db.relationship("StoreModel", back_populates="tags")
    items = db.relationship("ItemModel", back_populates="tags", secondary="items_tags")

class PlainTagSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()


class PlainItemSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    price = fields.Float(required=True)
class PlainStoreSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
class ItemSchema(PlainItemSchema):
    store_id = fields.Int(required=True, load_only=True)
    store = fields.Nested(PlainStoreSchema(), dump_only=True)
    tags = fields.List(fields.Nested(PlainTagSchema()), dump_only=True)


class ItemUpdateSchema(Schema):
    name = fields.Str()
    price = fields.Float()

class StoreSchema(PlainStoreSchema):
    items = fields.List(fields.Nested(PlainItemSchema()), dump_only=True)
    tags = fields.List(fields.Nested(PlainTagSchema()), dump_only=True)


class TagSchema(PlainTagSchema):
    store_id = fields.Int(load_only=True)
    store = fields.Nested(PlainStoreSchema(), dump_only=True)


class TagAndItemSchema(Schema):
    message = fields.Str()
    item = fields.Nested(ItemSchema)
    tag = fields.Nested(TagSchema)

items_tags = db.Table(
    "items_tags",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("item_id", db.Integer, db.ForeignKey("items.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"))
)

class Item(Resource):
    def get(self, name):
        item = ItemModel.query.filter_by(name=name).first() 
        if item:
            return ItemSchema().dump(item)
        return {"message": "Item not found"}, 404
    def post(self):
        data = request.get_json() 
        item = ItemModel(**data)
        db.session.add(item) 
        db.session.commit() 
        return ItemSchema().dump(item)
    def delete(self, name):
        item = ItemModel.query.filter_by(name=name).first()
        if item:
            db.session.delete(item)
            db.session.commit()
        return {"message": "Item deleted"}
class Store(Resource):
    def post(self):
        data = request.get_json()
        store = StoreModel(**data)
        db.session.add(store)
        db.session.commit()
        return StoreSchema().dump(store)
    def get(self, name):
        store = StoreModel.query.filter_by(name=name).first()
        if store:
            return StoreSchema().dump(store)
        return {"message": "Store not found"}, 404
    
    
class Tag(Resource):
    def post(self):
        data = request.get_json()
        tag = TagModel(**data)
        db.session.add(tag)
        db.session.commit()
        return TagSchema().dump(tag)

    def get(self, name):
        tag = TagModel.query.filter_by(name=name).first()
        if tag:
            return TagSchema().dump(tag)
        return {"message": "Tag not found"}, 404

    def delete(self, tag_id):
        tag = TagModel.query.get(tag_id)

        if len(tag.items) == 0:
            db.session.delete(tag)
            db.session.commit()
            return {"message": "Tag removed from item and deleted completely."}


class LinkTagToItem(Resource):
    def post(self, item_id, tag_id):
        item = ItemModel.query.get(item_id)
        tag = TagModel.query.get(tag_id)

        if not item or not tag:
            return {"message": "Item or Tag not found"}, 404

        item.tags.append(tag)
        db.session.commit()

        return TagAndItemSchema().dump({"message": "Tag added to Item", "item": item, "tag": tag})

    def delete(self, item_id, tag_id):
        item = ItemModel.query.get(item_id)
        tag = TagModel.query.get(tag_id)

        if not item or not tag:
            return {"message": "Item or Tag not found"}, 404

        if tag in item.tags:
            item.tags.remove(tag)
            db.session.commit()

            return {"message": "Tag removed from item."}

        return {"message": "Tag not attached to item."}, 400


api.add_resource(Item, '/item/<string:name>', '/item')
api.add_resource(Store, "/store/<string:name>", "/store")
api.add_resource(Tag, "/tag/<string:name>", "/tag")
api.add_resource(LinkTagToItem, "/item/<int:item_id>/tag/<int:tag_id>")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)