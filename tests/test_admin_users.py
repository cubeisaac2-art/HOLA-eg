from app import create_app
from models import db, User


def test_admin_can_delete_another_user_but_not_self():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        admin = User(email='delete-admin@test.com', username='deleteadmin', full_name='Delete Admin', role='admin', is_active=True)
        admin.password = 'admin123'
        user = User(email='delete-user@test.com', username='deleteuser', full_name='Delete User', role='user', is_active=True)
        user.password = 'user123'
        db.session.add_all([admin, user])
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = str(admin.id)
                session['_fresh'] = True

            response = client.post(f'/admin/users/{user.id}/delete')
            assert response.status_code == 302
            assert db.session.get(User, user.id) is None

            response = client.post(f'/admin/users/{admin.id}/delete')
            assert response.status_code == 302
            assert db.session.get(User, admin.id) is not None
