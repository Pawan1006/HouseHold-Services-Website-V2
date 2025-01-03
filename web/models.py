from . import db
from flask_login import UserMixin
from datetime import datetime
import pytz

# Admin model for admin users
class Admin(db.Model, UserMixin):
    __tablename = "admin"
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(150), unique = True)
    password = db.Column(db.String(50), nullable = False)

# User model for regular users
class User(db.Model, UserMixin):
    __tablename = "user"
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(150), unique = True)
    full_name = db.Column(db.String(150), nullable = False)
    address = db.Column(db.String(400), nullable = False)
    pincode = db.Column(db.Integer, nullable = False)
    password = db.Column(db.String(150), nullable = False)
    status = db.Column(db.String(50), default="active")

    requests = db.relationship('Request', backref='user', cascade="all, delete-orphan")


    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "address": self.address,
            "pincode": self.pincode,
            "status": self.status
        }
    
    
# Professional model for service providers
class Professional(db.Model, UserMixin):
    __tablename = "professional"
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(150), unique = True)
    full_name = db.Column(db.String(150), nullable = False)
    service = db.Column(db.String(150), nullable = False)
    experience = db.Column(db.Integer, nullable = False)
    address = db.Column(db.String(400), nullable = False)
    pincode = db.Column(db.Integer, nullable = False)
    password = db.Column(db.String(150), nullable = False)
    status = db.Column(db.String(50),default="pending")
    price = db.Column(db.Integer)
    desc = db.Column(db.Text)
    pdf_file_path = db.Column(db.String(250))

    @property
    def average_rating(self):
        """Calculate the average rating from all associated requests."""
        ratings = [request.rating for request in self.requests if request.rating is not None]
        if ratings:
            return sum(ratings) / len(ratings)
        return None
    

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "service": self.service,
            "experience": self.experience,
            "address": self.address,
            "pincode": self.pincode,
            "status": self.status,
            "price": self.price,
            "desc": self.desc if self.desc else "Not available",
            "pdf_file_path": self.pdf_file_path,
            "average_rating": self.average_rating
        }

# Service model for available services
class Service(db.Model):
    __tablename = "service"
    id = db.Column(db.Integer, primary_key = True)
    service = db.Column(db.String(150), nullable = False)
    desc = db.Column(db.Text)
    price = db.Column(db.Integer, nullable = False)

    def to_dict(self):
        return {
            "id": self.id,
            "service": self.service,
            "desc": self.desc if self.desc else "Not available",
            "price": self.price
        }

# Request model for service requests
class Request(db.Model):
    __tablename__ = "request"
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=True)
    date_of_request = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    date_of_completion = db.Column(db.DateTime)
    service_status = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    rating = db.Column(db.Integer)

    # Relationships
    service = db.relationship('Service', backref='requests')
    professional = db.relationship('Professional', backref='requests')
    customer = db.relationship('User', back_populates='requests', overlaps="user")

    def to_dict(self):
        return {
            "id": self.id,
            "service": self.service.to_dict() if self.service else None,
            "customer": self.customer.to_dict() if self.customer else None,
            "professional": self.professional.to_dict() if self.professional else None,
            "date_of_request": self.date_of_request.isoformat() if self.date_of_request else None,
            "date_of_completion": self.date_of_completion.isoformat() if self.date_of_completion else None,
            "service_status": self.service_status,
            "remarks": self.remarks if self.remarks else "Not available",
            "rating": self.rating if self.rating else "Not available"
        }