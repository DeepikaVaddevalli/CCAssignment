from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from datetime import date, datetime
from database import Session, create_tables, User, Stadium, Match, Seating, Booking
import random, string

app = FastAPI()

############## Pydantic Models ##############
# Pydantic models for request and response data
class PostUser(BaseModel):
	user_id: int

class GetMatch(BaseModel):
    match_id: int
    match_date: date
    match_time: str
    match_name: str
    stadium_id: int

class GetAvailability(BaseModel):
    seat_id: int
    stadium_id: int
    match_id: int
    stand_name: str
    seat_number: str

class PostBooking(BaseModel):
	match_id: int
	seat_ids: List[int]

class GetBooking(BaseModel):
	match_id: int
	match_date: date
	match_time: str
	match_name: str
	stadium_name: str
	stand_name: str
	seat_number: str
	booking_created_on: datetime
	booking_number: str


def get_db():
    db = Session
    try:
        yield db
    finally:
        db.close()


SESSION_USER = None

def get_current_user():
    return 1

def generate_booking_number(length=8):
    characters = string.ascii_uppercase + string.digits
    booking_number = ''.join(random.choice(characters) for _ in range(length))
    return booking_number

###################### Routes ######################

@app.post("/login_user", status_code=201)
def post_user(seats_to_book: PostBooking , db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):


# Route to get all matches
@app.get("/matches", response_model=List[GetMatch])
def get_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    
    if matches is None:
        raise HTTPException(status_code=404, detail="Matches not found!")
    return matches

# Route to check all vacant seats
@app.get("/availability/{match_id}", response_model=List[GetAvailability])
def get_availability(match_id: int, db: Session = Depends(get_db)):
    vacant_seats = (
        db.query(Seating.seat_id, Seating.stadium_id, Match.match_id, Seating.stand_name, Seating.seat_number)
        .outerjoin(Match, Match.stadium_id == Seating.stadium_id)
        .filter(Match.match_id == match_id)
        .filter(~Seating.seat_id.in_(db.query(Booking.seat_id).filter(Booking.match_id == match_id)))
    ).all()
    
    if vacant_seats is None:
        raise HTTPException(status_code=404, detail="All seats are booked!")
    return vacant_seats

# Route to book given vacant seats
@app.post("/book_seats", status_code=201)
def post_booking(seats_to_book: PostBooking , db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
	match_id = seats_to_book.match_id
	seats = seats_to_book.seat_ids
	booking_no = generate_booking_number()
	bookings = []

	for seat_id in seats:
		booking = Booking(booking_number=booking_no, match_id=match_id, seat_id=seat_id, user_id = current_user_id)
		bookings.append(booking)

	try:
		db.add_all(bookings)
		db.commit()
	except:
		raise HTTPException(status_code=409, detail="Conflict: One or more seats are already booked! Please try again")

	return "success"

# Route to get booked seats
@app.get("/get_bookings", response_model=List[GetBooking])
def get_bookings(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
	bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
	response = []
	for row in bookings:
		obj = GetBooking(match_id=row.match_id,
			match_date=row.booked_match.match_date,
			match_time=row.booked_match.match_time,
			match_name=row.booked_match.match_name,
			stadium_name=row.booked_match.stadium.name,
			stand_name=row.booked_seating.stand_name,
			seat_number=row.booked_seating.seat_number,
			booking_created_on=row.created_on,
			booking_number=row.booking_number)
		response.append(obj)
	return response


###################### Main ######################
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

