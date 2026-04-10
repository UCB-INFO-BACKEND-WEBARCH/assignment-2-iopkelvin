FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install flask flask-sqlalchemy flask-migrate psycopg2-binary redis rq marshmallow

CMD ["python", "app.py"]