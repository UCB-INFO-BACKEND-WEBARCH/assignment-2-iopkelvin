# Assignment 2 Grading: ortizkelvin

**Final Score: 100/100 (A+)**

## Summary
- Database Models: 20/20
- Task Endpoints: 30/30
- Category Endpoints: 15/15
- Background Tasks: 15/15
- Docker Compose: 20/20

## Detailed Results

### Database Models (20/20)

✅ **DB-01**: Task model has all required fields
   - Score: 8/8
   - All fields present: ['category', 'category_id', 'completed', 'created_at', 'description', 'due_date', 'id', 'title', 'updated_at']

✅ **DB-02**: Category model with unique name constraint
   - Score: 6/6
   - Correctly rejects duplicate category name (status 400)

✅ **DB-03**: Task-Category relationship (task belongs to category)
   - Score: 6/6
   - Task includes nested category object

### Task Endpoints with Validation (30/30)

✅ **TASK-01**: GET /tasks returns list of all tasks
   - Score: 4/4
   - Returns list of 2 tasks

✅ **TASK-02**: GET /tasks?completed=false filters by completion status
   - Score: 4/4
   - Filter works: completed=false returns 3, completed=true returns 1, all returns 4

✅ **TASK-03**: GET /tasks/:id returns single task with category info
   - Score: 3/3
   - Returns single task object

✅ **TASK-04**: GET /tasks/:id returns 404 when not found
   - Score: 2/2
   - Correctly returns 404

✅ **TASK-05**: POST /tasks creates task, returns 201
   - Score: 4/4
   - Creates task and returns 201 with task object

✅ **TASK-06**: POST /tasks validates input (title required, length limits)
   - Score: 4/4
   - Validation working: 4/4 tests passed

✅ **TASK-07**: Validation errors include structured messages
   - Score: 2/2
   - Structured error response: {"errors": {"title": ["Missing data for required field."]}}

✅ **TASK-08**: PUT /tasks/:id updates task, returns 200
   - Score: 3/3
   - Successfully updates task and returns updated object

✅ **TASK-09**: PUT /tasks/:id returns 404 when not found
   - Score: 1/1
   - Correctly returns 404

✅ **TASK-10**: DELETE /tasks/:id deletes task, returns 200 with message
   - Score: 2/2
   - Returns success for DELETE

✅ **TASK-11**: DELETE /tasks/:id returns 404 when not found
   - Score: 1/1
   - Correctly returns 404

### Category Endpoints (15/15)

✅ **CAT-01**: GET /categories returns categories with task_count
   - Score: 5/5
   - Returns 2 categories with task count

✅ **CAT-02**: GET /categories/:id returns category with its tasks
   - Score: 3/3
   - Returns category with tasks array (0 tasks)

✅ **CAT-03**: POST /categories validates unique name and hex color
   - Score: 4/4
   - Category validation working: 4/4 tests passed

✅ **CAT-04**: DELETE /categories/:id prevents deletion with existing tasks
   - Score: 3/3
   - Correctly prevents deletion of category with tasks (400)

### Background Task Processing (15/15)

✅ **BG-01**: Redis and rq worker properly configured
   - Score: 4/4
   - Redis and worker services defined in docker-compose.yml

✅ **BG-02**: notification_queued: true when due_date within 24h
   - Score: 5/5
   - Correctly returns notification_queued: true for imminent due date

✅ **BG-03**: notification_queued: false when no due_date or > 24h
   - Score: 3/3
   - Correctly returns false for no due_date and distant due_date

✅ **BG-04**: Background job executes (worker logs show reminder)
   - Score: 3/3
   - Worker logs show reminder message

### Docker Compose (20/20)

✅ **DOCK-01**: docker-compose.yml defines all 4 services (app, db, redis, worker)
   - Score: 5/5
   - All 4 services defined: ['app', 'db', 'redis', 'worker']

✅ **DOCK-02**: docker-compose up --build runs without errors
   - Score: 8/8
   - docker-compose up --build succeeded, all containers running

✅ **DOCK-03**: All services connect properly (app to db+redis, worker to redis)
   - Score: 4/4
   - Connectivity verified through functional endpoint tests

✅ **DOCK-04**: API is accessible and functional on configured port
   - Score: 3/3
   - API accessible at http://127.0.0.1:5050 (port 5050)

## Strengths
- docker-compose.yml defines all 4 services (app, db, redis, worker)
- Redis and rq worker properly configured
- docker-compose up --build runs without errors
- All services connect properly (app to db+redis, worker to redis)
- API is accessible and functional on configured port

## Areas for Improvement
- Great job! All rubric items passed.
