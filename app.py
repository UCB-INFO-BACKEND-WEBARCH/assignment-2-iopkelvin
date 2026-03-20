from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

app.config['SQLAlCHEMY_DATABASE_URI'] = 'sqlite://task_manager.db'
app.config['SQLAlCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class TaskModel(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable = False)
    description = db.Column(db.Text(500))
    completed = db.Column(db.Boolean, default = False)
    due_date = db.Column(db.DateTime) # ISO
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_at = db.Column(db.Datetime)
    updated_at = db.Column(db.Datetime)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "completed": self.completed,
            "due_date": self.due_date,
            "category_id": self.category_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class CategoryModel(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable = False) # unique
    color = db.Column(db.String(7)) # Hex

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
        }
    

@app.route('/api/categories/<int:task_id>', methods=["GET"])
def get_tasks():
    query = TaskModel.query
    


if __name__ == '__main__':
    app.run(debug=True)