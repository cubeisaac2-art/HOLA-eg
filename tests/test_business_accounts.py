from datetime import datetime, timedelta

from app import create_app
from models import db, User, Restaurant


def login_session(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True


def test_business_registration_starts_pending_subscription():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        with app.test_client() as client:
            response = client.post('/register', data={
                'full_name': 'Negocio Guinea',
                'username': 'negocioguinea',
                'email': 'negocio@test.com',
                'password': 'secret123',
                'account_type': 'business',
                'business_name': 'Restaurante Guinea',
                'subscription_plan': 'basic',
            })

            assert response.status_code == 302
            user = User.query.filter_by(username='negocioguinea').first()
            assert user.role == 'business'
            assert user.subscription_status == 'pending'
            assert user.subscription_plan == 'basic'


def test_active_business_can_create_owned_restaurant():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        user = User(
            email='active-business@test.com',
            username='activebusiness',
            full_name='Active Business',
            business_name='Comercio Activo',
            role='business',
            subscription_plan='basic',
            subscription_status='active',
            subscription_expires_at=datetime.utcnow() + timedelta(days=30),
            is_active=True,
        )
        user.password = 'secret123'
        db.session.add(user)
        db.session.commit()

        with app.test_client() as client:
            login_session(client, user)
            response = client.post('/admin/content/restaurant/new', data={
                'name': 'Restaurante del Bosque',
                'description': 'Cocina local y productos frescos.',
                'city': 'Bata',
                'address': 'Centro',
                'phone': '',
                'whatsapp': '',
                'price_level': 'medio',
                'stars': '4',
                'latitude': '1.86',
                'longitude': '9.75',
            })

            assert response.status_code == 302
            item = Restaurant.query.filter_by(name='Restaurante del Bosque').first()
            assert item is not None
            assert item.owner_id == user.id
