from app import create_app


def test_rumbo_malabo_travel_guides_are_available():
    app = create_app()
    response = app.test_client().get('/travel-guides')
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Vistazo a la isla de Bioko' in body
    assert 'Excursión a Ureka' in body
    assert 'rumbomalabo.com' in body
    assert 'info@rumbomalabo.com' in body


def test_history_information_page_is_available():
    app = create_app()
    response = app.test_client().get('/history')
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Historia e información de Guinea Ecuatorial' in body
    assert 'Etnografía y diversidad' in body
    assert 'wikipedia.org' in body
