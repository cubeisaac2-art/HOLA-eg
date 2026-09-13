from app import create_app
from models import db, FoodItem, Restaurant


def test_food_list_filters_by_query_and_city():
    app = create_app()

    with app.app_context():
        db.session.query(FoodItem).delete()
        db.session.query(Restaurant).delete()
        db.session.commit()

        db.session.add(FoodItem(name='Pepiá', description='Plato local', city='Malabo', price_level='medio', category='local', image='default-food.svg'))
        db.session.add(FoodItem(name='Fufu', description='Otro plato', city='Bata', price_level='bajo', category='local', image='default-food.svg'))
        db.session.commit()

        with app.test_client() as client:
            response = client.get('/food?q=pepi&city=Malabo')
            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert 'Pepiá' in body
            assert 'Fufu' not in body


def test_wikipedia_food_catalog_is_imported_with_sources_and_images():
    app = create_app()

    with app.app_context():
        foods = {item.name: item for item in FoodItem.query.all()}
        assert "Salsa de modica" in foods
        assert "Salsa de cacahuete" in foods
        assert foods["Salsa de modica"].image.startswith("https://commons.wikimedia.org/")
        assert foods["Salsa de cacahuete"].source_url == "https://es.wikipedia.org/wiki/Salsa_de_cacahuete"


def test_restaurant_list_filters_by_query():
    app = create_app()

    with app.app_context():
        db.session.query(Restaurant).delete()
        db.session.commit()

        db.session.add(Restaurant(name='La Casa del Mar', description='Mar', city='Malabo', address='A', phone='1', whatsapp='1', price_level='medio', stars=4, latitude=3.75, longitude=8.78, image='default-restaurant.svg'))
        db.session.add(Restaurant(name='Bata Grill', description='Carne', city='Bata', address='B', phone='2', whatsapp='2', price_level='alto', stars=5, latitude=1.86, longitude=9.76, image='default-restaurant.svg'))
        db.session.commit()

        with app.test_client() as client:
            response = client.get('/restaurants?q=grill')
            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert 'Bata Grill' in body
            assert 'La Casa del Mar' not in body
