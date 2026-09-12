from app import create_app
from models import db, User, FoodItem


def test_admin_can_edit_food_item():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        admin = User(email='edit-admin@test.com', username='editadmin', full_name='Edit Admin', role='admin', is_active=True)
        admin.password = 'admin123'
        item = FoodItem(name='Plato antiguo', description='Descripcion antigua.', city='Malabo', price_level='bajo', category='local')
        db.session.add_all([admin, item])
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = str(admin.id)
                session['_fresh'] = True

            response = client.post(f'/admin/content/food/{item.id}/edit', data={
                'name': 'Plato actualizado',
                'description': 'Descripcion actualizada y completa.',
                'city': 'Bata',
                'price_level': 'medio',
                'category': 'marino',
            })

            assert response.status_code == 302
            db.session.refresh(item)
            assert item.name == 'Plato actualizado'
            assert item.city == 'Bata'
            assert item.category == 'marino'
