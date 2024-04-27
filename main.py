from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Date, TIMESTAMP, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from pydantic import BaseModel
from typing import List
from datetime import date, datetime
import random, string
from mangum import Mangum

app = FastAPI()
handler = Mangum(app)

DATABASE_URL = "postgresql://Admin123:Aurora123@ticketingsystem.cluster-cxwiyci4eoxh.us-east-1.rds.amazonaws.com:5432/postgres"
#"sqlite:///ticketingsystemdb"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Session = SessionLocal()

Base = declarative_base()

class User(Base):
    __tablename__ = "user"
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    contact = Column(String)

    booked_bookings = relationship("Booking", back_populates="booked_user")

	

class Stadium(Base):
    __tablename__ = "stadium"
    stadium_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    city = Column(String)
    state = Column(String)
    seat_capacity = Column(Integer)

    matches = relationship("Match", back_populates="stadium")
    seatings = relationship("Seating", back_populates="stadium")

class Match(Base):
    __tablename__ = "match"
    match_id = Column(Integer, primary_key=True, index=True)
    match_date = Column(Date)
    match_time = Column(String)
    match_name = Column(String)
    stadium_id = Column(Integer, ForeignKey("stadium.stadium_id"))

    stadium = relationship("Stadium", back_populates="matches")
    booked_bookings = relationship("Booking", back_populates="booked_match")

class Seating(Base):
    __tablename__ = "seating"
    seat_id = Column(Integer, primary_key=True, index=True)
    stadium_id = Column(Integer, ForeignKey("stadium.stadium_id"))
    stand_name = Column(String)
    seat_number = Column(String)

    stadium = relationship("Stadium", back_populates="seatings")
    booked_bookings = relationship("Booking", back_populates="booked_seating")

class Booking(Base):
    __tablename__ = "booking"
    booking_number = Column(String, primary_key=True)
    match_id = Column(Integer, ForeignKey("match.match_id"), primary_key=True)
    seat_id = Column(Integer, ForeignKey("seating.seat_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.user_id"))
    created_on = Column(TIMESTAMP, default=datetime.utcnow)

    booked_match = relationship("Match", back_populates="booked_bookings")
    booked_seating = relationship("Seating", back_populates="booked_bookings")
    booked_user = relationship("User", back_populates="booked_bookings")


def create_tables():
	Base.metadata.create_all(bind=engine)



############## Pydantic Models ##############
# Pydantic models for request and response data
class GetUser(BaseModel):
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
	user_id: int

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

def generate_booking_number(length=8):
    characters = string.ascii_uppercase + string.digits
    booking_number = ''.join(random.choice(characters) for _ in range(length))
    return booking_number

###################### Routes ######################

@app.get("/")
async def hello():
	return {"message":"success"}

@app.get("/login_user", response_model=GetUser)
async def get_user(db: Session = Depends(get_db)):
	users = db.query(User.user_id).all()

	user_list = []
	for row in users:
		user_list.append(row.user_id)
	
	obj = GetUser(user_id = random.randint(1, max(user_list)))
	return obj


# Route to get all matches
@app.get("/matches", response_model=List[GetMatch])
async def get_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    
    if matches is None:
        raise HTTPException(status_code=404, detail="Matches not found!")
    return matches

# Route to check all vacant seats
@app.get("/availability/{match_id}", response_model=List[GetAvailability])
async def get_availability(match_id: int, db: Session = Depends(get_db)):
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
@app.post("/book_seats/", status_code=201)
async def post_booking(seats_to_book: PostBooking , db: Session = Depends(get_db)):
	match_id = seats_to_book.match_id
	seats = seats_to_book.seat_ids
	userid = seats_to_book.user_id
	booking_no = generate_booking_number()
	bookings = []
	print("current_user is : ",userid)
	for seat_id in seats:
		booking = Booking(booking_number=booking_no, match_id=match_id, seat_id=seat_id, user_id = userid)
		bookings.append(booking)

	print(bookings)
	try:
		db.add_all(bookings)
		db.commit()
	except:
		raise HTTPException(status_code=409, detail="Conflict: One or more seats are already booked! Please try again")

	return "success"

# Route to get booked seats
@app.get("/get_bookings", response_model=List[GetBooking])
async def get_bookings(user_id: int, db: Session = Depends(get_db)):
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



