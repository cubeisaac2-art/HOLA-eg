from app import create_app
from models import db, User, NewsArticle


def test_admin_can_create_and_edit_news():
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        admin = User(email="news-admin@test.com", username="newsadmin", full_name="News Admin", role="admin", is_active=True)
        admin.password = "admin123"
        db.session.add(admin)
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["_user_id"] = str(admin.id)
                session["_fresh"] = True

            response = client.post("/admin/content/news/new", data={
                "title": "Nueva noticia local",
                "summary": "Un resumen suficientemente largo para superar la validación.",
                "body": "Contenido de la noticia con información relevante para la comunidad local.",
                "category": "actualidad",
                "source_url": "https://example.com/noticia",
            })

            assert response.status_code == 302
            article = NewsArticle.query.filter_by(title="Nueva noticia local").first()
            assert article is not None

            response = client.post(f"/admin/content/news/{article.id}/edit", data={
                "title": "Noticia local actualizada",
                "summary": "Resumen actualizado suficientemente largo para superar la validación.",
                "body": "Contenido actualizado con información relevante para la comunidad local.",
                "category": "sociedad",
                "source_url": "https://example.com/actualizada",
            })

            assert response.status_code == 302
            db.session.refresh(article)
            assert article.title == "Noticia local actualizada"
            assert article.category == "sociedad"