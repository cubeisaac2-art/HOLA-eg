from app import create_app
from models import db, User, FoodItem, Hotel


def test_seeded_hotels_have_catalog_data_and_images():
    app = create_app()

    with app.app_context():
        hotels = {item.name: item for item in Hotel.query.all()}

        assert len(hotels) >= 7
        assert hotels["Hotel Sofitel Malabo Sipopo Le Golf"].image == "imgns/hotel sofitel.jpg"
        assert hotels["Hotel Sofitel Malabo Sipopo Le Golf"].latitude == 3.7915
        assert hotels["Grand Hotel Bata"].longitude == 9.7540


def test_admin_can_edit_hotel_item():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        admin = User(email='edit-hotel-admin@test.com', username='edithoteladmin', full_name='Edit Hotel Admin', role='admin', is_active=True)
        admin.password = 'admin123'
        item = Hotel(name='Hotel temporal', description='Descripcion antigua.', city='Malabo', price_level='medio', stars=3, latitude=3.75, longitude=8.72)
        db.session.add_all([admin, item])
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = str(admin.id)
                session['_fresh'] = True

            response = client.post(f'/admin/content/hotel/{item.id}/edit', data={
                'name': 'Hotel actualizado',
                'description': 'Descripcion actualizada y completa.',
                'city': 'Bata',
                'address': 'Paseo maritimo',
                'phone': '',
                'website': '',
                'price_level': 'alto',
                'stars': '5',
                'latitude': '1.8615',
                'longitude': '9.754',
            })

            assert response.status_code == 302
            db.session.refresh(item)
            assert item.name == 'Hotel actualizado'
            assert item.city == 'Bata'
            assert item.stars == 5


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
