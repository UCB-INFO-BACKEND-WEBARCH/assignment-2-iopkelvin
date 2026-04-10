import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
# from marshmallow import Schema, fields, validates, ValidationError
from datetime import datetime, timezone, timedelta
from redis import Redis
from rq import Queue
import time

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///task_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
def validate_task(data):
    errors = {}
    title = data.get("title")
    if not title:
        return {"error": "Title is required"}
    if not title or len(title) > 100:
        errors["title"] = ["Length must be between 1 and 100."]
    description = data.get("description")
    if description and len(description) > 500:
        errors["description"] = ["Max 500 characters"]
    if "category_id" in data and data["category_id"]:
        if not db.session.get(CategoryModel, data["category_id"]):
            errors["category_id"] = ["Invalid category_id"]
    return errors if errors else None

def validate_category(data):
    if not data or "name" not in data:
        return {"error": "Name is required"}
    if len(data["name"]) > 50:
        return {"error": "Name too long"}
    if CategoryModel.query.filter_by(name=data["name"]).first():
        return {"error": "Category already exists"}
    if "color" in data and data["color"]:
        color = data["color"]
        if not isinstance(color, str) or len(color) != 7 or color[0] != "#":
            return {"error": "Invalid hex color"}
        hex_part = color[1:]
        if not all(c in "0123456789abcdefABCDEF" for c in hex_part):
            return {"error": "Invalid hex color"}
    return None


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
    return jsonify([t.to_dict() for t in tasks]), 200


@app.route('/tasks/<int:id>', methods=['GET'])
def get_task(id):
    task = db.get_or_404(TaskModel, id)
    return jsonify(task.to_dict()), 200



@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    error = validate_task(data)
    if error:
        return jsonify(error), 400

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"])
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
        except:
            return jsonify({"error": "Invalid ISO format"}), 400
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

    for field in ["title", "description", "completed", "category_id"]:
        if field in data:
            setattr(task, field, data[field])

    if "due_date" in data:
        if data["due_date"]:
            try:
                dt = datetime.fromisoformat(data["due_date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                task.due_date = dt
            except:
                return jsonify({"error": "Invalid ISO format"}), 400
        else:
            task.due_date = None
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
    return jsonify([c.to_dict() for c in CategoryModel.query.all()])


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
    error = validate_category(data)
    if error:
        return jsonify(error), 400
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
        return jsonify({"error": "Cannot delete category with existing tasks"}), 400

    db.session.delete(cat)
    db.session.commit()

    return jsonify({"message": "Category deleted"}), 200


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)