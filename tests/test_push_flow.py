from app import create_app, send_push_notification
from models import db, PushSubscription, User


def test_send_push_notification_for_active_subscriptions(monkeypatch):
    app = create_app()

    with app.app_context():
        db.session.query(PushSubscription).delete()
        db.session.query(User).delete()
        db.session.commit()

        admin = User(
            email="admin@test.com",
            username="admin",
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        admin.password = "admin123"
        db.session.add(admin)
        db.session.commit()

        sub = PushSubscription(
            user_id=admin.id,
            endpoint="https://example.com/push-endpoint",
            p256dh="test-p256dh",
            auth="test-auth",
            is_active=True,
        )
        db.session.add(sub)
        db.session.commit()

        calls = []

        def fake_webpush(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr("app.webpush", fake_webpush)

        send_push_notification(target_scope="all", title="Test title", body="Test body")

        assert len(calls) == 1
        assert calls[0]["subscription_info"]["endpoint"] == "https://example.com/push-endpoint"
