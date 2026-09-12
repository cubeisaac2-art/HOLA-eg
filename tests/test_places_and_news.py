from app import create_app
from models import db, User, PlaceRecommendation


def test_news_categories_and_visa_link():
    app = create_app()
    with app.app_context():
        client = app.test_client()
        response = client.get('/news?category=deporte')
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert 'Agenda deportiva local' in body
        assert 'Memoria viva de Malabo' not in body

        visa_response = client.get('/visa')
        assert visa_response.status_code == 302
        assert visa_response.location == app.config['EMBASSY_VISA_URL']


def test_authenticated_user_can_recommend_a_place():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.session.query(PlaceRecommendation).delete()
        user = User(
            email='traveler@test.com',
            username='traveler',
            full_name='Local Traveler',
            role='user',
            is_active=True,
        )
        user.password = 'secret123'
        db.session.add(user)
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = str(user.id)
                session['_fresh'] = True

            response = client.post('/places/recommend', data={
                'name': 'Sendero del bosque',
                'description': 'Un sendero tranquilo para conocer la naturaleza local.',
                'city': 'Bata',
                'category': 'naturaleza',
                'address': 'Zona forestal',
            })

            assert response.status_code == 302
            recommendation = PlaceRecommendation.query.filter_by(name='Sendero del bosque').first()
            assert recommendation is not None
            assert recommendation.status == 'pending'


def test_only_approved_places_are_public():
    app = create_app()
    with app.app_context():
        user = User.query.first()
        if user is None:
            user = User(email='places@test.com', username='places', full_name='Places User', role='user')
            user.password = 'secret123'
            db.session.add(user)
            db.session.flush()
        db.session.query(PlaceRecommendation).delete()
        db.session.add(PlaceRecommendation(user_id=user.id, name='Lugar pendiente', description='Pendiente de revisión.', city='Malabo', status='pending'))
        db.session.add(PlaceRecommendation(user_id=user.id, name='Lugar publicado', description='Publicado para todos.', city='Malabo', status='approved'))
        db.session.commit()
        response = app.test_client().get('/places')
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'Lugar publicado' in body
        assert 'Lugar pendiente' not in body
