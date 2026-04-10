import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
# from marshmallow import Schema, fields, validates, ValidationError
from datetime import datetime
from redis import Redis
from rq import Queue


app = Flask(__name__)

app.config['SQLAlCHEMY_DATABASE_URI'] = 'sqlite://task_manager.db'
app.config['SQLAlCHEMY_TRACK_MODIFICATIONS'] = False
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
    created_at = db.Column(db.Datetime, default=datetime.datetime)
    updated_at = db.Column(db.Datetime, default=datetime.datetime, onupdate=datetime.datetime),
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
    name = db.Column(db.String(50), required = True) # unique
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
    if not title or len(title) > 100:
        errors["title"] = ["Length must be between 1 and 100."]

    description = data.get("description")
    if description and len(description) > 500:
        errors["description"] = ["Max 500 characters"]

    if "due_date" in data:
        try:
            datetime.fromisoformat(data["due_date"])
        except:
            errors["due_date"] = ["Invalid ISO format"]

    if "category_id" in data and data["category_id"] is not None:
        if not db.session.get(CategoryModel, data["category_id"]):
            errors["category_id"] = ["Invalid category_id"]
    return errors

def validate_category(data):
    errors = {}

    name = data.get("name")
    if not name or len(name) > 50:
        errors["name"] = ["Invalid name"]


    if name and CategoryModel.query.filter_by(name=name).first():
        errors["name"] = ["Category with this name already exists."]

    # color = data.get("color")
    # if color and not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        # errors["color"] = ["Invalid hex color"]
    return errors



# Routes
@app.route("/tasks", methods=["GET"])
def get_tasks():
    completed = request.args.get("completed")
    query = TaskModel.query

    if completed is not None:
        query = query.filter_by(completed=(completed.lower() == "true"))
    
    tasks = query.all()
    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "category_id": task.category_id,
            "category": {
                "id": task.category.id,
                "name": task.category.name,
                "color": task.category.color
            } if task.category else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        })
    return {"tasks": result}, 200

@app.route('/tasks/<int:id>', methods=["GET"])
def get_task(id):
    task = db.session.get(TaskModel, id)

    if not task:
        return {"error": "Task not found"}, 404

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "category_id": task.category_id,
        "category": {
            "id": task.category.id,
            "name": task.category.name,
            "color": task.category.color
        } if task.category else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat()
    }, 200


@app.route('/api/categories/<int:task_id>', methods=["GET"])
def get_tasks():
    query = TaskModel.query

if __name__ == '__main__':
    app.run(debug=True)