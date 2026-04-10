import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime, timezone, timedelta
from redis import Redis
from rq import Queue
import time
from flask_migrate import Migrate


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Redis Queue
redis_conn = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379)
q = Queue(connection=redis_conn)


class TaskModel(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable = False)
    description = db.Column(db.String(500))
    completed = db.Column(db.Boolean, default = False)
    due_date = db.Column(db.DateTime) # ISO
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "completed": self.completed,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    

class CategoryModel(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True) # unique
    color = db.Column(db.String(7)) # Hex
    tasks = db.relationship("TaskModel", backref="category")
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "task_count": len(self.tasks)
        }

# Validation
class TaskSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(allow_none=True, validate=validate.Length(max=500))
    due_date = fields.DateTime(allow_none=True)
    category_id = fields.Int(allow_none=True)
    completed = fields.Bool(load_default=False)


class CategorySchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    color = fields.Str(
        allow_none=True,
        validate=validate.Regexp(r'^#[0-9a-fA-F]{6}$')
    )

task_schema = TaskSchema()
category_schema = CategorySchema()


def send_notification(title):
    time.sleep(5)
    print(f"Reminder: Task '{title}' is due soon!")

# Routes
@app.route("/tasks", methods=["GET"])
def get_tasks():
    query = TaskModel.query
    completed = request.args.get('completed')
    if completed == "true":
        query = query.filter_by(completed=True)
    elif completed == "false":
        query = query.filter_by(completed=False)

    tasks = query.all()
    return jsonify({"tasks": [t.to_dict() for t in tasks]}), 200


@app.route('/tasks/<int:id>', methods=['GET'])
def get_task(id):
    task = db.get_or_404(TaskModel, id)
    return jsonify(task.to_dict()), 200



@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data:
        return jsonify({"errors": {"json": ["Invalid or missing JSON"]}}), 400

    try:
        data = task_schema.load(data) 
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    if data.get("category_id"):
        if not db.session.get(CategoryModel, data["category_id"]):
            return jsonify({"errors": {"category_id": ["Invalid category_id"]}}), 400

    due_date = data.get("due_date")
    if due_date and due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    task = TaskModel(
        title=data["title"],
        description=data.get("description"),
        due_date=due_date,
        category_id=data.get("category_id")
    )
    db.session.add(task)
    db.session.commit()

    notification_queued = False
    if due_date:
        now = datetime.now(timezone.utc)
        if now < due_date <= now + timedelta(hours=24):
            q.enqueue(send_notification, task.title)
            notification_queued = True

    return jsonify({
        "task": task.to_dict(),
        "notification_queued": notification_queued
    }), 201


@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    task = db.get_or_404(TaskModel, id)
    data = request.get_json()
    if not data:
        return jsonify({"errors": {"json": ["Invalid or missing JSON"]}}), 400

    try:
        data = task_schema.load(data, partial=True)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    if "category_id" in data:
        if data["category_id"] and not db.session.get(CategoryModel, data["category_id"]):
            return jsonify({"errors": {"category_id": ["Invalid category_id"]}}), 400

    if "due_date" in data:
        due_date = data.get("due_date")
        if due_date and due_date.tzinfo is None:
            data["due_date"] = due_date.replace(tzinfo=timezone.utc)

    for key, value in data.items():
        setattr(task, key, value)

    db.session.commit()

    return jsonify(task.to_dict()), 200


@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = db.get_or_404(TaskModel, id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"}), 200


@app.route('/categories', methods=['GET'])
def get_categories():
    return jsonify({"categories": [c.to_dict() for c in CategoryModel.query.all()]}), 200


@app.route('/categories/<int:id>', methods=['GET'])
def get_category(id):
    cat = db.get_or_404(CategoryModel, id)
    return jsonify({
        "id": cat.id,
        "name": cat.name,
        "color": cat.color,
        "tasks": [
            {"id": t.id, "title": t.title, "completed": t.completed}
            for t in cat.tasks
        ]
    })


@app.route('/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    if not data:
        return jsonify({"errors": {"json": ["Invalid or missing JSON"]}}), 400

    try:
        data = category_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # uniqueness check (business logic)
    if CategoryModel.query.filter_by(name=data["name"]).first():
        return jsonify({
            "errors": {"name": ["Category with this name already exists."]}
        }), 400
    category = CategoryModel(
        name=data["name"],
        color=data.get("color")
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@app.route('/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    cat = db.get_or_404(CategoryModel, id)

    if len(cat.tasks) > 0:
        return jsonify({
    "error": "Cannot delete category with existing tasks. Move or delete tasks first."
    }), 400

    db.session.delete(cat)
    db.session.commit()

    return jsonify({"message": "Category deleted"}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)