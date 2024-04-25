#install locust - pip install locust
#locust -f locust_test.py


from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):
    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        pass
    
    @task(1)
    def get_matches(self):
        self.client.get("/matches")
    
    @task(2)
    def get_availability(self):
        self.client.get("/availability/1")  # Assuming match_id=1 for demonstration
    
    @task(3)
    def book_seats(self):
        data = {
            "match_id": 1,  # Assuming match_id=1 for demonstration
            "seat_ids": [1, 2, 3]  # Assuming seat_ids for booking
        }
        self.client.post("/book_seats", json=data)

class WebsiteUser(HttpUser):
    host = "http://127.0.0.1:8000"  # FastAPI server address
    wait_time = between(5, 15)  # Time between consecutive requests

    tasks = [UserBehavior]

