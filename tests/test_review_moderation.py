from app import create_app
from models import db, User, Review


def test_toggle_review_approval_requires_admin():
    app = create_app()

    with app.app_context():
        db.session.query(Review).delete()
        db.session.query(User).delete()
        db.session.commit()

        admin = User(
            email="admin-review@test.com",
            username="adminreview",
            full_name="Admin Review",
            role="admin",
            is_active=True,
        )
        admin.password = "admin123"
        db.session.add(admin)
        db.session.commit()

        review = Review(
            user_id=admin.id,
            content_type="restaurant",
            content_id=1,
            rating=4,
            comment="Muy bueno",
            is_approved=True,
        )
        db.session.add(review)
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = str(admin.id)
                session['_fresh'] = True

            response = client.post(f"/admin/reviews/{review.id}/toggle-approval")
            assert response.status_code == 302

            review_after = Review.query.get(review.id)
            assert review_after.is_approved is False
