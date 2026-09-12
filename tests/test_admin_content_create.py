from app import create_app
from models import db, User, FoodItem


def test_admin_can_create_food_item():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.session.query(FoodItem).delete()
        db.session.query(User).delete()
        db.session.commit()

        admin = User(
            email='admin-content@test.com',
            username='admincontent',
            full_name='Admin Content',
            role='admin',
            is_active=True,
        )
        admin.password = 'admin123'
        db.session.add(admin)
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = str(admin.id)
                session['_fresh'] = True

            response = client.post('/admin/content/food/new', data={
                'name': 'Caldo de pescado',
                'description': 'Caldo tradicional de Guinea.',
                'city': 'Malabo',
                'price_level': 'medio',
                'category': 'local',
            })

            assert response.status_code == 302
            food = FoodItem.query.filter_by(name='Caldo de pescado').first()
            assert food is not None
            assert food.city == 'Malabo'
