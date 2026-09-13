from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    business_name = db.Column(db.String(150), default="")
    subscription_plan = db.Column(db.String(20), default="basic", nullable=False)
    subscription_status = db.Column(db.String(20), default="none", nullable=False)
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    profile_image = db.Column(db.String(255), default="default-avatar.svg")
    bio = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    favorites = db.relationship("Favorite", backref="user", cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="user", cascade="all, delete-orphan")
    dictionary_entries = db.relationship(
        "DictionaryEntry",
        backref="creator",
        foreign_keys="DictionaryEntry.created_by_id",
        cascade="all, delete-orphan",
    )
    push_subscriptions = db.relationship("PushSubscription", backref="user", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="user", cascade="all, delete-orphan")

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def can_manage_dictionary(self):
        return self.role in {"admin", "editor"}

    @property
    def is_business(self):
        return self.role == "business"

    @property
    def content_limit(self):
        return None if self.subscription_plan == "pro" else 3

    @property
    def password(self):
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, plain_password):
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password):
        return check_password_hash(self.password_hash, plain_password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "profile_image": self.profile_image,
            "bio": self.bio,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DictionaryEntry(db.Model):
    __tablename__ = "dictionary_entries"

    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(120), nullable=False, index=True)
    translation = db.Column(db.String(180), nullable=False)
    language = db.Column(db.String(40), nullable=False, default="fang")
    category = db.Column(db.String(60), nullable=False, default="general")
    notes = db.Column(db.Text, default="")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "term": self.term,
            "translation": self.translation,
            "language": self.language,
            "category": self.category,
            "notes": self.notes,
            "created_by": self.creator.full_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FoodItem(db.Model):
    __tablename__ = "food_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    price_level = db.Column(db.String(20), default="moderado")
    category = db.Column(db.String(40), default="local")
    recipe = db.Column(db.Text, default="")
    video_url = db.Column(db.String(500), default="")
    image = db.Column(db.String(255), default="default-food.svg")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def average_rating(self):
        ratings = [review.rating for review in self.reviews]
        if not ratings:
            return 0
        return round(sum(ratings) / len(ratings), 2)

    @property
    def review_count(self):
        return len(self.reviews)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "city": self.city,
            "price_level": self.price_level,
            "category": self.category,
            "recipe": self.recipe,
            "video_url": self.video_url,
            "image": self.image,
            "average_rating": self.average_rating,
            "review_count": self.review_count,
        }


class Restaurant(db.Model):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(200), default="")
    phone = db.Column(db.String(50), default="")
    whatsapp = db.Column(db.String(50), default="")
    price_level = db.Column(db.String(20), default="moderado")
    stars = db.Column(db.Integer, default=3)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), default="default-restaurant.svg")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def average_rating(self):
        ratings = [review.rating for review in self.reviews]
        if not ratings:
            return 0
        return round(sum(ratings) / len(ratings), 2)

    @property
    def review_count(self):
        return len(self.reviews)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "city": self.city,
            "address": self.address,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "price_level": self.price_level,
            "stars": self.stars,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image": self.image,
            "average_rating": self.average_rating,
            "review_count": self.review_count,
        }


class Hotel(db.Model):
    __tablename__ = "hotels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(200), default="")
    phone = db.Column(db.String(50), default="")
    website = db.Column(db.String(200), default="")
    price_level = db.Column(db.String(20), default="moderado")
    stars = db.Column(db.Integer, default=3)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), default="default-hotel.svg")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def average_rating(self):
        ratings = [review.rating for review in self.reviews]
        if not ratings:
            return 0
        return round(sum(ratings) / len(ratings), 2)

    @property
    def review_count(self):
        return len(self.reviews)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "city": self.city,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "price_level": self.price_level,
            "stars": self.stars,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image": self.image,
            "average_rating": self.average_rating,
            "review_count": self.review_count,
        }


class PlaceRecommendation(db.Model):
    __tablename__ = "place_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(40), nullable=False, default="cultura")
    address = db.Column(db.String(200), default="")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    image = db.Column(db.String(255), default="default-place.svg")
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recommender = db.relationship("User", backref="place_recommendations")


class NewsArticle(db.Model):
    __tablename__ = "news_articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    summary = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False, default="actualidad")
    image = db.Column(db.String(255), default="default-news.svg")
    source_url = db.Column(db.String(500), default="")
    published_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "category": self.category,
            "image": self.image,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)
    content_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "content_type", "content_id", name="unique_favorite"),)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)
    content_id = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, default="")
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "content_type", "content_id", name="unique_user_review_per_item"),)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "rating": self.rating,
            "comment": self.comment,
            "is_approved": self.is_approved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PushSubscription(db.Model):
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class NotificationLog(db.Model):
    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    target_scope = db.Column(db.String(30), nullable=False, default="all")
    target_user_id = db.Column(db.Integer, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
