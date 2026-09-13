import os
import re
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from pywebpush import webpush
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect, text

from config import config
from forms import (
    LoginForm,
    RegisterForm,
    ProfileForm,
    DictionaryForm,
    FoodForm,
    RestaurantForm,
    HotelForm,
    PlaceRecommendationForm,
    NewsForm,
    RoleForm,
    SubscriptionForm,
    ReviewForm,
    NotificationForm,
)
from models import db, User, DictionaryEntry, FoodItem, Restaurant, Hotel, PlaceRecommendation, NewsArticle, Favorite, Review, PushSubscription, NotificationLog, ActivityLog
from utils import save_upload_image


login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def log_activity(user_id, action, details=""):
    activity = ActivityLog(user_id=user_id, action=action, details=details)
    db.session.add(activity)
    db.session.commit()


def dish_slug(name):
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "plato"


def import_bundled_fang_dictionary():
    source_path = Path(__file__).resolve().parent / "diccionario_fang_espanol (1).txt"
    if not source_path.exists():
        return
    admin = User.query.filter_by(email="admin@holaguinea.com").first()
    if admin is None:
        return
    pattern = re.compile(r"^(?P<term>[^\t]+?)\s+(?:\d+(?:/\d+)?\s+)?(?:pref\.|ext\.)?\s*(?P<marker>n\.|ad\. v\.|interj\.?|interr\.?|prep\.?|conj\.?|afirm\.?|neg\.?|indef\.?|num\.?|pos\. pers\.?|in\. v\.)\s+(?P<meaning>.+)$", re.IGNORECASE)
    added = 0
    for raw_line in source_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw_line.strip())
        if not match:
            continue
        term = re.sub(r"^[¹²'\"*]+|[¹²'\"*]+$", "", match.group("term")).strip(" ,")
        translation = re.sub(r"\s+", " ", match.group("meaning").split(";", 1)[0].strip())
        if not term or len(term) > 120 or not translation or len(translation) > 180:
            continue
        exists = DictionaryEntry.query.filter_by(term=term, translation=translation, language="fang").first()
        if exists:
            continue
        db.session.add(DictionaryEntry(term=term, translation=translation, language="fang", category="general", notes="Importado de la sección Fang-Español, letra A.", created_by_id=admin.id))
        added += 1
    if added:
        db.session.commit()


def send_push_notification(target_scope="all", title="HOLA GUINEA", body="Nueva actualización disponible.", target_user_id=None):
    if not app:
        return False

    vapid_private = app.config.get("VAPID_PRIVATE_KEY")
    vapid_public = app.config.get("VAPID_PUBLIC_KEY")
    vapid_claim_email = app.config.get("VAPID_CLAIM_EMAIL")

    if not vapid_private or not vapid_public:
        return False

    query = PushSubscription.query.filter_by(is_active=True)
    if target_scope == "user" and target_user_id is not None:
        query = query.filter_by(user_id=target_user_id)

    subscriptions = query.all()
    if not subscriptions:
        return False

    payload = {
        "title": title,
        "body": body,
        "icon": "/static/icons/icon-192.svg",
        "badge": "/static/icons/icon-192.svg",
        "data": {"url": "/"},
    }

    for subscription in subscriptions:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=str(payload).replace("'", '"'),
            vapid_private_key=vapid_private,
            vapid_claim_email=vapid_claim_email,
            vapid_public_key=vapid_public,
        )

    return True


def ensure_schema_columns():
    food_columns = {column["name"] for column in inspect(db.engine).get_columns("food_items")}
    if "recipe" not in food_columns:
        db.session.execute(text("ALTER TABLE food_items ADD COLUMN recipe TEXT DEFAULT ''"))
    if "video_url" not in food_columns:
        db.session.execute(text("ALTER TABLE food_items ADD COLUMN video_url VARCHAR(500) DEFAULT ''"))
    migrations = {
        "users": [
            ("business_name", "VARCHAR(150) DEFAULT ''"),
            ("subscription_plan", "VARCHAR(20) DEFAULT 'basic' NOT NULL"),
            ("subscription_status", "VARCHAR(20) DEFAULT 'none' NOT NULL"),
            ("subscription_expires_at", "TIMESTAMP"),
        ],
        "restaurants": [("owner_id", "INTEGER")],
        "hotels": [("owner_id", "INTEGER")],
    }
    for table, columns in migrations.items():
        existing_columns = {column["name"] for column in inspect(db.engine).get_columns(table)}
        for column_name, definition in columns:
            if column_name not in existing_columns:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}"))
    db.session.commit()


app = None


def create_app(config_name: str = "default"):
    global app
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @app.before_request
    def set_language_context():
        if "language" not in session:
            session["language"] = app.config.get("DEFAULT_LANGUAGE", "es")

    with app.app_context():
        db.create_all()
        ensure_schema_columns()
        seed_data()
        import_bundled_fang_dictionary()

    @app.context_processor
    def share_helpers():
        def media_url(image, upload_folder="uploads"):
            image = image or ""
            if image.startswith("imgns/"):
                return url_for("static", filename=image)
            return url_for("static", filename=f"{upload_folder}/{image}")

        def public_url(endpoint, **values):
            path = url_for(endpoint, **values)
            base_url = app.config.get("PUBLIC_BASE_URL")
            return f"{base_url}{path}" if base_url else url_for(endpoint, _external=True, **values)

        return {"public_url": public_url, "dish_slug": dish_slug, "media_url": media_url}

    @app.route("/set-language/<lang>")
    def set_language(lang):
        if lang in app.config.get("LANGUAGES", ["es", "fr"]):
            session["language"] = lang
        return redirect(request.referrer or url_for("index"))

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/travel-guides")
    def travel_guides():
        packages = [
            ("Vistazo a la isla de Bioko", "4 días", "https://rumbomalabo.com/vistazo-a-la-isla-de-bioko-2/"),
            ("Explorador de Bioko", "5 días", "https://rumbomalabo.com/explorador-de-bioko/"),
            ("La joya de Bioko", "7 días", "https://rumbomalabo.com/la-joya-de-bioko/"),
            ("Los secretos de Bioko", "9 días", "https://rumbomalabo.com/los-secretos-de-bioko/"),
            ("La belleza de Guinea Ecuatorial", "10 días", "https://rumbomalabo.com/la-belleza-de-guinea-ecuatorial/"),
            ("Islas de Guinea Ecuatorial", "12 días", "https://rumbomalabo.com/islas-de-guinea-ecuatorial/"),
        ]
        excursions = [
            ("Excursión a Ureka", "1 o 2 días", "https://rumbomalabo.com/tour-a-ureka/"),
            ("Visita al Lago Biao", "1 día", "https://rumbomalabo.com/visita-al-lago-biao/"),
            ("Pico Basilé", "Medio día", "https://rumbomalabo.com/excursion-al-pico-basile/"),
            ("Cascadas Ilachi", "1 día", "https://rumbomalabo.com/visita-a-cascadas-iladyi/"),
            ("Tour por la Isla de Bioko", "1 día", "https://rumbomalabo.com/tour-isla-bioko/"),
            ("Excursión a Corisco", "3 días", "https://rumbomalabo.com/viaje-corisco/"),
            ("Cascadas de Bilelipa", "1 día", "https://rumbomalabo.com/cascadas-bilelipa-guinea-ecuatorial/"),
            ("Tour a Monte Alen", "2 días", "https://rumbomalabo.com/monte-alen/"),
        ]
        return render_template("travel_guides.html", packages=packages, excursions=excursions)

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/places")
    def places():
        category = request.args.get("category", "all")
        query = PlaceRecommendation.query.filter_by(status="approved")
        if category != "all":
            query = query.filter_by(category=category)
        recommendations = query.order_by(PlaceRecommendation.created_at.desc()).all()
        return render_template("places/list.html", recommendations=recommendations, category=category)

    @app.route("/places/recommend", methods=["GET", "POST"])
    @login_required
    def recommend_place():
        form = PlaceRecommendationForm()
        if form.validate_on_submit():
            image_path = "default-place.svg"
            if form.image.data:
                image_path = save_upload_image(form.image.data, folder="places")
            recommendation = PlaceRecommendation(
                user_id=current_user.id,
                name=form.name.data.strip(),
                description=form.description.data.strip(),
                city=form.city.data.strip(),
                category=form.category.data,
                address=(form.address.data or "").strip(),
                latitude=form.latitude.data,
                longitude=form.longitude.data,
                image=image_path,
            )
            db.session.add(recommendation)
            db.session.commit()
            log_activity(current_user.id, "place_recommended", f"Sitio recomendado: {recommendation.name}")
            flash("Gracias. Tu recomendación será revisada antes de publicarse.", "success")
            return redirect(url_for("places"))
        return render_template("places/form.html", form=form)

    @app.route("/news")
    def news():
        category = request.args.get("category", "all")
        query = NewsArticle.query.filter_by(is_published=True)
        if category != "all":
            query = query.filter_by(category=category)
        articles = query.order_by(NewsArticle.published_at.desc()).all()
        return render_template("news/list.html", articles=articles, category=category)

    @app.route("/news/<int:article_id>")
    def news_detail(article_id):
        article = NewsArticle.query.filter_by(id=article_id, is_published=True).first_or_404()
        return render_template("news/detail.html", article=article)

    @app.route("/visa")
    def visa():
        return redirect(app.config["EMBASSY_VISA_URL"])

    @app.route("/register", methods=["GET", "POST"])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data.lower()).first():
                flash("Este correo ya existe.", "danger")
                return redirect(url_for("register"))

            user = User(
                email=form.email.data.lower(),
                username=form.username.data.strip(),
                full_name=form.full_name.data.strip(),
                role=form.account_type.data,
                business_name=(form.business_name.data or "").strip(),
                subscription_plan=form.subscription_plan.data,
                subscription_status="pending" if form.account_type.data == "business" else "none",
            )
            user.password = form.password.data
            db.session.add(user)
            db.session.commit()
            log_activity(user.id, "register", "Usuario registrado en la plataforma")
            login_user(user)
            if user.is_business:
                flash("Cuenta creada. Solicita y acredita tu suscripción para publicar tu negocio.", "info")
                return redirect(url_for("business_dashboard"))
            flash("¡Registro completado con éxito!", "success")
            return redirect(url_for("index"))
        return render_template("auth/register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower()).first()
            if user and user.check_password(form.password.data) and user.is_active:
                login_user(user)
                log_activity(user.id, "login", "Inicio de sesión correcto")
                flash("Bienvenido de nuevo.", "success")
                return redirect(url_for("index"))
            flash("Credenciales incorrectas o usuario inactivo.", "danger")
        return render_template("auth/login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        log_activity(current_user.id, "logout", "Cierre de sesión")
        logout_user()
        flash("Sesión cerrada.", "info")
        return redirect(url_for("login"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        form = ProfileForm(obj=current_user)
        if form.validate_on_submit():
            current_user.full_name = form.full_name.data
            current_user.username = form.username.data
            current_user.bio = form.bio.data
            if form.profile_image.data:
                filename = save_upload_image(form.profile_image.data, folder="profiles")
                current_user.profile_image = filename
            db.session.commit()
            log_activity(current_user.id, "profile_update", "Perfil actualizado")
            flash("Perfil actualizado.", "success")
            return redirect(url_for("profile"))
        return render_template("auth/profile.html", form=form)

    @app.route("/business")
    @login_required
    def business_dashboard():
        if not current_user.is_business:
            return redirect(url_for("profile"))
        restaurants = Restaurant.query.filter_by(owner_id=current_user.id).order_by(Restaurant.created_at.desc()).all()
        hotels = Hotel.query.filter_by(owner_id=current_user.id).order_by(Hotel.created_at.desc()).all()
        subscription_active = current_user.subscription_status == "active" and (current_user.subscription_expires_at is None or current_user.subscription_expires_at > datetime.utcnow())
        return render_template("business/dashboard.html", restaurants=restaurants, hotels=hotels, subscription_active=subscription_active)

    @app.route("/business/subscribe", methods=["GET", "POST"])
    @login_required
    def business_subscribe():
        if not current_user.is_business:
            return redirect(url_for("profile"))
        form = SubscriptionForm(obj=current_user)
        form.plan.data = current_user.subscription_plan
        if form.validate_on_submit():
            current_user.subscription_plan = form.plan.data
            current_user.subscription_status = "pending"
            current_user.subscription_expires_at = None
            db.session.commit()
            flash("Solicitud enviada. Un administrador activará la suscripción tras confirmar el pago.", "info")
            return redirect(url_for("business_dashboard"))
        return render_template("business/subscribe.html", form=form)

    @app.route("/dictionary")
    def dictionary():
        language = request.args.get("language", "all")
        query = request.args.get("q", "")
        q = DictionaryEntry.query
        if language != "all":
            q = q.filter_by(language=language)
        if query:
            q = q.filter(DictionaryEntry.term.ilike(f"%{query}%") | DictionaryEntry.translation.ilike(f"%{query}%"))
        entries = q.order_by(DictionaryEntry.term).all()
        return render_template("dictionary/list.html", entries=entries, language=language, query=query)

    @app.route("/dictionary/new", methods=["GET", "POST"])
    @login_required
    def new_dictionary_entry():
        if not current_user.can_manage_dictionary:
            flash("No tienes permisos para gestionar el diccionario.", "danger")
            return redirect(url_for("dictionary"))
        form = DictionaryForm()
        if form.validate_on_submit():
            entry = DictionaryEntry(
                term=form.term.data.strip(),
                translation=form.translation.data.strip(),
                language=form.language.data,
                category=form.category.data,
                notes=form.notes.data or "",
                created_by_id=current_user.id,
            )
            db.session.add(entry)
            db.session.commit()
            log_activity(current_user.id, "dictionary_entry_added", f"Entrada añadida: {entry.term}")
            flash("Entrada añadida correctamente.", "success")
            return redirect(url_for("dictionary"))
        return render_template("dictionary/form.html", form=form)

    @app.route("/food")
    def food_list():
        query = request.args.get("q", "").strip()
        city = request.args.get("city", "").strip()
        items_query = FoodItem.query

        if query:
            items_query = items_query.filter(FoodItem.name.ilike(f"%{query}%") | FoodItem.description.ilike(f"%{query}%"))
        if city:
            items_query = items_query.filter(FoodItem.city.ilike(f"%{city}%"))

        items = items_query.order_by(FoodItem.created_at.desc()).all()
        return render_template("food/list.html", items=items, query=query, city=city)

    @app.route("/food/<int:item_id>")
    def food_detail(item_id):
        item = FoodItem.query.get_or_404(item_id)
        form = ReviewForm()
        reviews = Review.query.filter_by(content_type="food", content_id=item_id).order_by(Review.created_at.desc()).all()
        is_favorite = False
        if current_user.is_authenticated:
            is_favorite = Favorite.query.filter_by(user_id=current_user.id, content_type="food", content_id=item_id).first() is not None
        return render_template("food/detail.html", item=item, reviews=reviews, form=form, is_favorite=is_favorite)

    @app.route("/plato/<slug>-<int:item_id>")
    def shared_food_detail(item_id, slug):
        return redirect(url_for("food_detail", item_id=item_id), code=301)

    @app.route("/restaurants")
    def restaurants():
        query = request.args.get("q", "").strip()
        city = request.args.get("city", "").strip()
        items_query = Restaurant.query

        if query:
            items_query = items_query.filter(Restaurant.name.ilike(f"%{query}%") | Restaurant.description.ilike(f"%{query}%"))
        if city:
            items_query = items_query.filter(Restaurant.city.ilike(f"%{city}%"))

        items = items_query.order_by(Restaurant.created_at.desc()).all()
        return render_template("restaurants/list.html", items=items, query=query, city=city)

    @app.route("/restaurants/<int:item_id>")
    def restaurant_detail(item_id):
        item = Restaurant.query.get_or_404(item_id)
        form = ReviewForm()
        reviews = Review.query.filter_by(content_type="restaurant", content_id=item_id).order_by(Review.created_at.desc()).all()
        is_favorite = False
        if current_user.is_authenticated:
            is_favorite = Favorite.query.filter_by(user_id=current_user.id, content_type="restaurant", content_id=item_id).first() is not None
        return render_template("restaurants/detail.html", item=item, reviews=reviews, form=form, is_favorite=is_favorite)

    @app.route("/hotels")
    def hotels():
        items = Hotel.query.order_by(Hotel.created_at.desc()).all()
        return render_template("hotels/list.html", items=items)

    @app.route("/hotels/<int:item_id>")
    def hotel_detail(item_id):
        item = Hotel.query.get_or_404(item_id)
        form = ReviewForm()
        reviews = Review.query.filter_by(content_type="hotel", content_id=item_id).order_by(Review.created_at.desc()).all()
        is_favorite = False
        if current_user.is_authenticated:
            is_favorite = Favorite.query.filter_by(user_id=current_user.id, content_type="hotel", content_id=item_id).first() is not None
        return render_template("hotels/detail.html", item=item, reviews=reviews, form=form, is_favorite=is_favorite)

    @app.route("/map")
    def map_view():
        restaurants = Restaurant.query.all()
        hotels = Hotel.query.all()
        return render_template("map.html", restaurants=restaurants, hotels=hotels)

    @app.route("/favorites")
    @login_required
    def favorites():
        favorite_items = []
        for favorite in Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all():
            item = None
            item_url = "#"
            item_label = "Elemento eliminado"
            item_type = favorite.content_type

            if favorite.content_type == "food":
                item = FoodItem.query.get(favorite.content_id)
                if item:
                    item_label = item.name
                    item_url = url_for("food_detail", item_id=item.id)
            elif favorite.content_type == "restaurant":
                item = Restaurant.query.get(favorite.content_id)
                if item:
                    item_label = item.name
                    item_url = url_for("restaurant_detail", item_id=item.id)
            elif favorite.content_type == "hotel":
                item = Hotel.query.get(favorite.content_id)
                if item:
                    item_label = item.name
                    item_url = url_for("hotel_detail", item_id=item.id)

            favorite_items.append({
                "content_type": item_type,
                "content_id": favorite.content_id,
                "label": item_label,
                "url": item_url,
                "created_at": favorite.created_at,
            })

        return render_template("favorites.html", favorites=favorite_items)

    @app.route("/api/subscribe", methods=["POST"])
    @login_required
    def subscribe_push():
        data = request.get_json(silent=True) or {}
        endpoint = data.get("endpoint")
        p256dh = data.get("keys", {}).get("p256dh") if isinstance(data.get("keys"), dict) else None
        auth = data.get("keys", {}).get("auth") if isinstance(data.get("keys"), dict) else None

        if not endpoint or not p256dh or not auth:
            return jsonify({"status": "error", "message": "Datos de suscripción incompletos."}), 400

        existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if existing:
            existing.user_id = current_user.id
            existing.p256dh = p256dh
            existing.auth = auth
            existing.is_active = True
        else:
            db.session.add(PushSubscription(user_id=current_user.id, endpoint=endpoint, p256dh=p256dh, auth=auth, is_active=True))

        db.session.commit()
        return jsonify({"status": "ok"})

    @app.route("/favorite/<content_type>/<int:content_id>", methods=["POST"])
    @login_required
    def toggle_favorite(content_type, content_id):
        valid_types = {"food", "restaurant", "hotel"}
        if content_type not in valid_types:
            return jsonify({"status": "error", "message": "Tipo no válido."}), 400

        existing = Favorite.query.filter_by(user_id=current_user.id, content_type=content_type, content_id=content_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            log_activity(current_user.id, "favorite_removed", f"Favorito eliminado: {content_type}:{content_id}")
            return jsonify({"status": "removed"})

        favorite = Favorite(user_id=current_user.id, content_type=content_type, content_id=content_id)
        db.session.add(favorite)
        db.session.commit()
        log_activity(current_user.id, "favorite_added", f"Favorito añadido: {content_type}:{content_id}")
        return jsonify({"status": "added"})

    @app.route("/review/<content_type>/<int:content_id>", methods=["POST"])
    @login_required
    def submit_review(content_type, content_id):
        form = ReviewForm()
        if form.validate_on_submit():
            review = Review(
                user_id=current_user.id,
                content_type=content_type,
                content_id=content_id,
                rating=form.rating.data,
                comment=form.comment.data,
            )
            db.session.add(review)
            db.session.commit()
            log_activity(current_user.id, "review_added", f"Reseña añadida a {content_type}:{content_id} ({form.rating.data}★)")
            flash("Reseña guardada.", "success")
        else:
            flash("La reseña no pudo guardarse.", "danger")
        return redirect(request.referrer or url_for("index"))

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        stats = {
            "users": User.query.count(),
            "dictionary_entries": DictionaryEntry.query.count(),
            "food_items": FoodItem.query.count(),
            "restaurants": Restaurant.query.count(),
            "hotels": Hotel.query.count(),
            "recommendations": PlaceRecommendation.query.count(),
            "news": NewsArticle.query.count(),
            "reviews": Review.query.count(),
            "favorites": Favorite.query.count(),
        }
        recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        return render_template("admin/dashboard.html", stats=stats, recent_activity=recent_activity)

    @app.route("/admin/users")
    @login_required
    def admin_users():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template("admin/users.html", users=users)

    @app.route("/admin/users/<int:user_id>/role", methods=["POST"])
    @login_required
    def update_user_role(user_id):
        if not current_user.is_admin:
            return jsonify({"status": "forbidden"}), 403
        user = User.query.get_or_404(user_id)
        form = RoleForm()
        if form.validate_on_submit():
            user.role = form.role.data
            db.session.commit()
            flash("Rol actualizado correctamente.", "success")
        else:
            flash("El rol seleccionado no es válido.", "danger")
        return redirect(url_for("admin_users"))

    @app.route("/admin/users/<int:user_id>/subscription", methods=["POST"])
    @login_required
    def update_user_subscription(user_id):
        if not current_user.is_admin:
            return jsonify({"status": "forbidden"}), 403
        user = User.query.get_or_404(user_id)
        if user.role != "business":
            flash("Solo las cuentas de negocio tienen suscripciones.", "warning")
            return redirect(url_for("admin_users"))
        action = request.form.get("action")
        if action == "activate":
            user.subscription_status = "active"
            user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
            flash(f"Suscripción de {user.business_name or user.username} activada durante 30 días.", "success")
        elif action == "expire":
            user.subscription_status = "expired"
            user.subscription_expires_at = datetime.utcnow()
            flash("Suscripción marcada como vencida.", "info")
        db.session.commit()
        return redirect(url_for("admin_users"))

    @app.route("/admin/dictionary")
    @login_required
    def admin_dictionary():
        if not current_user.can_manage_dictionary:
            flash("No tienes permisos para gestionar el diccionario.", "danger")
            return redirect(url_for("index"))
        entries = DictionaryEntry.query.order_by(DictionaryEntry.term).all()
        return render_template("admin/dictionary.html", entries=entries)

    @app.route("/admin/dictionary/new", methods=["GET", "POST"])
    @login_required
    def admin_new_dictionary_entry():
        if not current_user.can_manage_dictionary:
            flash("No tienes permisos para gestionar el diccionario.", "danger")
            return redirect(url_for("index"))
        form = DictionaryForm()
        if form.validate_on_submit():
            entry = DictionaryEntry(
                term=form.term.data.strip(),
                translation=form.translation.data.strip(),
                language=form.language.data,
                category=form.category.data,
                notes=(form.notes.data or "").strip(),
                created_by_id=current_user.id,
            )
            db.session.add(entry)
            db.session.commit()
            flash("Palabra añadida correctamente.", "success")
            return redirect(url_for("admin_dictionary"))
        return render_template("dictionary/form.html", form=form, title="Nueva palabra", submit_label="Añadir palabra")

    @app.route("/admin/dictionary/<int:entry_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_edit_dictionary_entry(entry_id):
        if not current_user.can_manage_dictionary:
            flash("No tienes permisos para gestionar el diccionario.", "danger")
            return redirect(url_for("index"))
        entry = DictionaryEntry.query.get_or_404(entry_id)
        form = DictionaryForm(obj=entry)
        if form.validate_on_submit():
            entry.term = form.term.data.strip()
            entry.translation = form.translation.data.strip()
            entry.language = form.language.data
            entry.category = form.category.data
            entry.notes = (form.notes.data or "").strip()
            db.session.commit()
            flash("Palabra actualizada correctamente.", "success")
            return redirect(url_for("admin_dictionary"))
        return render_template("dictionary/form.html", form=form, title="Editar palabra", submit_label="Guardar cambios")

    @app.route("/admin/dictionary/<int:entry_id>/delete", methods=["POST"])
    @login_required
    def admin_delete_dictionary_entry(entry_id):
        if not current_user.can_manage_dictionary:
            return jsonify({"status": "forbidden"}), 403
        entry = DictionaryEntry.query.get_or_404(entry_id)
        db.session.delete(entry)
        db.session.commit()
        flash("Palabra eliminada correctamente.", "success")
        return redirect(url_for("admin_dictionary"))

    @app.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
    @login_required
    def toggle_user_status(user_id):
        if not current_user.is_admin:
            return jsonify({"status": "forbidden"}), 403
        user = User.query.get_or_404(user_id)
        user.is_active = not user.is_active
        db.session.commit()
        return jsonify({"status": "ok", "active": user.is_active})

    @app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    def delete_user(user_id):
        if not current_user.is_admin:
            return jsonify({"status": "forbidden"}), 403
        if current_user.id == user_id:
            flash("No puedes eliminar tu propia cuenta de administrador.", "warning")
            return redirect(url_for("admin_users"))

        user = User.query.get_or_404(user_id)
        if user.is_admin and User.query.filter_by(role="admin", is_active=True).count() <= 1:
            flash("Debe quedar al menos un administrador activo.", "warning")
            return redirect(url_for("admin_users"))

        db.session.delete(user)
        db.session.commit()
        flash("Usuario eliminado correctamente.", "success")
        return redirect(url_for("admin_users"))

    @app.route("/admin/content")
    @login_required
    def admin_content():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        foods = FoodItem.query.order_by(FoodItem.created_at.desc()).all()
        restaurants = Restaurant.query.order_by(Restaurant.created_at.desc()).all()
        hotels = Hotel.query.order_by(Hotel.created_at.desc()).all()
        dictionary = DictionaryEntry.query.order_by(DictionaryEntry.created_at.desc()).all()
        recommendations = PlaceRecommendation.query.order_by(PlaceRecommendation.created_at.desc()).all()
        articles = NewsArticle.query.order_by(NewsArticle.published_at.desc()).all()
        return render_template("admin/content.html", foods=foods, restaurants=restaurants, hotels=hotels, dictionary=dictionary, recommendations=recommendations, articles=articles)

    @app.route("/admin/content/recommendations/<int:recommendation_id>/toggle", methods=["POST"])
    @login_required
    def toggle_recommendation(recommendation_id):
        if not current_user.is_admin:
            return jsonify({"status": "forbidden"}), 403
        recommendation = PlaceRecommendation.query.get_or_404(recommendation_id)
        recommendation.status = "approved" if recommendation.status != "approved" else "hidden"
        db.session.commit()
        flash("Estado de la recomendación actualizado.", "success")
        return redirect(url_for("admin_content"))

    @app.route("/admin/content/news/new", methods=["GET", "POST"])
    @login_required
    def admin_new_news():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        form = NewsForm()
        if form.validate_on_submit():
            image_path = "default-news.svg"
            if form.image.data:
                image_path = save_upload_image(form.image.data, folder="news")
            article = NewsArticle(
                title=form.title.data.strip(),
                summary=form.summary.data.strip(),
                body=form.body.data.strip(),
                category=form.category.data,
                source_url=(form.source_url.data or "").strip(),
                image=image_path,
            )
            db.session.add(article)
            db.session.commit()
            log_activity(current_user.id, "news_created", f"Noticia publicada: {article.title}")
            flash("Noticia publicada correctamente.", "success")
            return redirect(url_for("admin_content"))
        return render_template("admin/news_form.html", form=form)

    @app.route("/admin/content/news/<int:article_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_edit_news(article_id):
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        article = NewsArticle.query.get_or_404(article_id)
        form = NewsForm(obj=article)
        if form.validate_on_submit():
            article.title = form.title.data.strip()
            article.summary = form.summary.data.strip()
            article.body = form.body.data.strip()
            article.category = form.category.data
            article.source_url = (form.source_url.data or "").strip()
            if getattr(form.image.data, "filename", ""):
                article.image = save_upload_image(form.image.data, folder="news")
            db.session.commit()
            log_activity(current_user.id, "news_updated", f"Noticia actualizada: {article.title}")
            flash("Noticia actualizada correctamente.", "success")
            return redirect(url_for("admin_content"))
        return render_template("admin/news_form.html", form=form, title="Editar noticia", submit_label="Guardar cambios")

    @app.route("/admin/content/food/new", methods=["GET", "POST"])
    @login_required
    def admin_new_food():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))

        form = FoodForm()
        if form.validate_on_submit():
            image_path = "default-food.svg"
            if form.image.data:
                image_path = save_upload_image(form.image.data, folder="food")

            item = FoodItem(
                name=form.name.data.strip(),
                description=form.description.data.strip(),
                city=form.city.data.strip(),
                price_level=form.price_level.data,
                category=form.category.data,
                recipe=(form.recipe.data or "").strip(),
                video_url=(form.video_url.data or "").strip(),
                image=image_path,
            )
            db.session.add(item)
            db.session.commit()
            log_activity(current_user.id, "food_created", f"Comida creada: {item.name}")
            flash("Comida añadida correctamente.", "success")
            return redirect(url_for("admin_content"))

        return render_template("admin/content_form.html", form=form, title="Nueva comida", submit_label="Crear comida", action_url=url_for("admin_new_food"))

    @app.route("/admin/content/food/<int:item_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_edit_food(item_id):
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        item = FoodItem.query.get_or_404(item_id)
        form = FoodForm(obj=item)
        if form.validate_on_submit():
            item.name = form.name.data.strip()
            item.description = form.description.data.strip()
            item.city = form.city.data.strip()
            item.price_level = form.price_level.data
            item.category = form.category.data
            item.recipe = (form.recipe.data or "").strip()
            item.video_url = (form.video_url.data or "").strip()
            if getattr(form.image.data, "filename", ""):
                item.image = save_upload_image(form.image.data, folder="food")
            db.session.commit()
            log_activity(current_user.id, "food_updated", f"Comida actualizada: {item.name}")
            flash("Comida actualizada correctamente.", "success")
            return redirect(url_for("admin_content"))
        return render_template("admin/content_form.html", form=form, title="Editar comida", submit_label="Guardar cambios", action_url=url_for("admin_edit_food", item_id=item.id))

    @app.route("/admin/content/restaurant/new", methods=["GET", "POST"])
    @login_required
    def admin_new_restaurant():
        if not current_user.is_admin:
            if not current_user.is_business:
                flash("No tienes permisos para gestionar negocios.", "danger")
                return redirect(url_for("index"))
            if current_user.subscription_status != "active" or (current_user.subscription_expires_at and current_user.subscription_expires_at <= datetime.utcnow()):
                flash("Necesitas una suscripción activa para publicar.", "warning")
                return redirect(url_for("business_subscribe"))
            owned_count = Restaurant.query.filter_by(owner_id=current_user.id).count() + Hotel.query.filter_by(owner_id=current_user.id).count()
            if current_user.subscription_plan != "pro" and owned_count >= 3:
                flash("El plan de 250 FCFA permite hasta 3 publicaciones.", "warning")
                return redirect(url_for("business_dashboard"))
        if current_user.is_admin or current_user.is_business:
            pass
        else:
            return redirect(url_for("index"))

        form = RestaurantForm()
        if form.validate_on_submit():
            image_path = "default-restaurant.svg"
            if form.image.data:
                image_path = save_upload_image(form.image.data, folder="restaurants")

            item = Restaurant(
                name=form.name.data.strip(),
                description=form.description.data.strip(),
                city=form.city.data.strip(),
                address=form.address.data.strip(),
                phone=form.phone.data.strip(),
                whatsapp=form.whatsapp.data.strip(),
                price_level=form.price_level.data,
                stars=form.stars.data or 3,
                latitude=form.latitude.data,
                longitude=form.longitude.data,
                image=image_path,
                owner_id=current_user.id if current_user.is_business else None,
            )
            db.session.add(item)
            db.session.commit()
            log_activity(current_user.id, "restaurant_created", f"Restaurante creado: {item.name}")
            flash("Restaurante añadido correctamente.", "success")
            return redirect(url_for("business_dashboard" if current_user.is_business else "admin_content"))

        return render_template("admin/content_form.html", form=form, title="Nuevo restaurante", submit_label="Crear restaurante", action_url=url_for("admin_new_restaurant"))

    @app.route("/admin/content/restaurant/<int:item_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_edit_restaurant(item_id):
        if not current_user.is_admin and not current_user.is_business:
            flash("No tienes permisos para gestionar negocios.", "danger")
            return redirect(url_for("index"))
        item = Restaurant.query.filter_by(id=item_id, **({"owner_id": current_user.id} if current_user.is_business else {})).first_or_404()
        form = RestaurantForm(obj=item)
        if form.validate_on_submit():
            item.name = form.name.data.strip()
            item.description = form.description.data.strip()
            item.city = form.city.data.strip()
            item.address = (form.address.data or "").strip()
            item.phone = (form.phone.data or "").strip()
            item.whatsapp = (form.whatsapp.data or "").strip()
            item.price_level = form.price_level.data
            item.stars = form.stars.data or 3
            item.latitude = form.latitude.data
            item.longitude = form.longitude.data
            if getattr(form.image.data, "filename", ""):
                item.image = save_upload_image(form.image.data, folder="restaurants")
            db.session.commit()
            log_activity(current_user.id, "restaurant_updated", f"Restaurante actualizado: {item.name}")
            flash("Restaurante actualizado correctamente.", "success")
            return redirect(url_for("business_dashboard" if current_user.is_business else "admin_content"))
        return render_template("admin/content_form.html", form=form, title="Editar restaurante", submit_label="Guardar cambios", action_url=url_for("admin_edit_restaurant", item_id=item.id))

    @app.route("/admin/content/hotel/new", methods=["GET", "POST"])
    @login_required
    def admin_new_hotel():
        if not current_user.is_admin:
            if not current_user.is_business:
                flash("No tienes permisos para gestionar negocios.", "danger")
                return redirect(url_for("index"))
            if current_user.subscription_status != "active" or (current_user.subscription_expires_at and current_user.subscription_expires_at <= datetime.utcnow()):
                flash("Necesitas una suscripción activa para publicar.", "warning")
                return redirect(url_for("business_subscribe"))
            owned_count = Restaurant.query.filter_by(owner_id=current_user.id).count() + Hotel.query.filter_by(owner_id=current_user.id).count()
            if current_user.subscription_plan != "pro" and owned_count >= 3:
                flash("El plan de 250 FCFA permite hasta 3 publicaciones.", "warning")
                return redirect(url_for("business_dashboard"))
        if not current_user.is_admin and not current_user.is_business:
            return redirect(url_for("index"))

        form = HotelForm()
        if form.validate_on_submit():
            image_path = "default-hotel.svg"
            if form.image.data:
                image_path = save_upload_image(form.image.data, folder="hotels")

            item = Hotel(
                name=form.name.data.strip(),
                description=form.description.data.strip(),
                city=form.city.data.strip(),
                address=form.address.data.strip(),
                phone=form.phone.data.strip(),
                website=form.website.data.strip(),
                price_level=form.price_level.data,
                stars=form.stars.data or 3,
                latitude=form.latitude.data,
                longitude=form.longitude.data,
                image=image_path,
                owner_id=current_user.id if current_user.is_business else None,
            )
            db.session.add(item)
            db.session.commit()
            log_activity(current_user.id, "hotel_created", f"Hotel creado: {item.name}")
            flash("Hotel añadido correctamente.", "success")
            return redirect(url_for("business_dashboard" if current_user.is_business else "admin_content"))

        return render_template("admin/content_form.html", form=form, title="Nuevo hotel", submit_label="Crear hotel", action_url=url_for("admin_new_hotel"))

    @app.route("/admin/content/hotel/<int:item_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_edit_hotel(item_id):
        if not current_user.is_admin and not current_user.is_business:
            flash("No tienes permisos para gestionar negocios.", "danger")
            return redirect(url_for("index"))
        item = Hotel.query.filter_by(id=item_id, **({"owner_id": current_user.id} if current_user.is_business else {})).first_or_404()
        form = HotelForm(obj=item)
        if form.validate_on_submit():
            item.name = form.name.data.strip()
            item.description = form.description.data.strip()
            item.city = form.city.data.strip()
            item.address = (form.address.data or "").strip()
            item.phone = (form.phone.data or "").strip()
            item.website = (form.website.data or "").strip()
            item.price_level = form.price_level.data
            item.stars = form.stars.data or 3
            item.latitude = form.latitude.data
            item.longitude = form.longitude.data
            if getattr(form.image.data, "filename", ""):
                item.image = save_upload_image(form.image.data, folder="hotels")
            db.session.commit()
            log_activity(current_user.id, "hotel_updated", f"Hotel actualizado: {item.name}")
            flash("Hotel actualizado correctamente.", "success")
            return redirect(url_for("business_dashboard" if current_user.is_business else "admin_content"))
        return render_template("admin/content_form.html", form=form, title="Editar hotel", submit_label="Guardar cambios", action_url=url_for("admin_edit_hotel", item_id=item.id))

    @app.route("/admin/reviews")
    @login_required
    def admin_reviews():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        reviews = Review.query.order_by(Review.created_at.desc()).all()
        return render_template("admin/reviews.html", reviews=reviews)

    @app.route("/admin/reviews/<int:review_id>/toggle-approval", methods=["POST"])
    @login_required
    def toggle_review_approval(review_id):
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))

        review = Review.query.get_or_404(review_id)
        review.is_approved = not review.is_approved
        db.session.commit()
        flash("Estado de la reseña actualizado.", "success")
        return redirect(url_for("admin_reviews"))

    @app.route("/admin/export/csv")
    @login_required
    def admin_export_csv():
        if not current_user.is_admin:
            return jsonify({"status": "forbidden"}), 403

        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["model", "field", "value"])

        for user in User.query.all():
            writer.writerow(["user", "email", user.email])
            writer.writerow(["user", "role", user.role])

        for entry in DictionaryEntry.query.all():
            writer.writerow(["dictionary", "term", entry.term])

        response = app.response_class(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=hola-guinea-export.csv"
        return response

    @app.route("/admin/notifications", methods=["GET", "POST"])
    @login_required
    def admin_notifications():
        if not current_user.is_admin:
            flash("No tienes permisos de administrador.", "danger")
            return redirect(url_for("index"))
        form = NotificationForm()
        if form.validate_on_submit():
            log = NotificationLog(
                title=form.title.data,
                body=form.body.data,
                target_scope=form.target_scope.data,
                target_user_id=form.target_user_id.data or None,
                created_by_id=current_user.id,
            )
            db.session.add(log)
            db.session.commit()
            send_push_notification(
                target_scope=form.target_scope.data,
                title=form.title.data,
                body=form.body.data,
                target_user_id=form.target_user_id.data,
            )
            flash("Notificación registrada correctamente.", "success")
            return redirect(url_for("admin_notifications"))
        return render_template("admin/send_notification.html", form=form)

    @app.route("/api/health")
    def health_check():
        return jsonify({"status": "ok", "application": "HOLA GUINEA"})

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    return app


def seed_data():
    if User.query.filter_by(email="admin@holaguinea.com").first() is None:
        admin_username = "admin" if User.query.filter_by(username="admin").first() is None else "admin-holaguinea"
        admin = User(
            email="admin@holaguinea.com",
            username=admin_username,
            full_name="Administrador HOLA GUINEA",
            role="admin",
            is_active=True,
        )
        admin.password = "admin123"
        db.session.add(admin)

    if DictionaryEntry.query.count() == 0:
        entries = [
            ("Mba", "Hola", "fang", "saludo", "Uso cotidiano para saludar."),
            ("Nde", "Agua", "bubi", "naturaleza", "Palabra usada en la costa."),
            ("Nzi", "Comida", "ndowe", "alimentación", "Término básico."),
        ]
        for term, translation, language, category, notes in entries:
            db.session.add(DictionaryEntry(term=term, translation=translation, language=language, category=category, notes=notes, created_by_id=1))

    if FoodItem.query.count() == 0:
        db.session.add_all(
            [
                FoodItem(name="Pepiá", description="Plato tradicional ecuatoguineano a base de pescado y caldo.", city="Malabo", price_level="medio", category="local", image="default-food.svg"),
                FoodItem(name="Fufu con caldo", description="Comida reconfortante con harina de yuca y caldo de pollo.", city="Bata", price_level="bajo", category="local", image="default-food.svg"),
            ]
        )

    if Restaurant.query.count() == 0:
        db.session.add_all(
            [
                Restaurant(name="La Casa del Mar", description="Restaurante cercano al malecón.", city="Malabo", address="Av. de la Costa", phone="+240000000", whatsapp="+240000000", price_level="medio", stars=4, latitude=3.753, longitude=8.782, image="default-restaurant.svg"),
                Restaurant(name="Bata Grill", description="Especialidad en carnes y cocina local.", city="Bata", address="Centro urbano", phone="+240111111", whatsapp="+240111111", price_level="medio", stars=5, latitude=1.863, longitude=9.768, image="default-restaurant.svg"),
            ]
        )

    hotel_catalog = [
        {
            "name": "Hotel Sofitel Malabo Sipopo Le Golf",
            "description": "Exclusivo resort de 5 estrellas en Sipopo, con playa privada, campo de golf profesional de 18 hoyos, spa, piscina y restaurantes de cocina francesa e internacional.",
            "city": "Malabo",
            "address": "Sipopo",
            "website": "https://all.accor.com/hotel/8212/index.es.shtml",
            "price_level": "alto",
            "stars": 5,
            "latitude": 3.7915,
            "longitude": 8.8710,
            "image": "imgns/hotel sofitel.jpg",
        },
        {
            "name": "Hotel Bisila Palace",
            "description": "Hotel de 5 estrellas situado a 1,2 kilómetros del Aeropuerto de Malabo, con habitaciones climatizadas, wifi, piscina exterior, jardines, gimnasio y restaurante buffet.",
            "city": "Malabo",
            "address": "Malabo, cerca del aeropuerto",
            "price_level": "alto",
            "stars": 5,
            "latitude": 3.7554,
            "longitude": 8.7244,
            "image": "imgns/bisila palace.jpg",
        },
        {
            "name": "Hotel Anda China",
            "description": "Hotel de la zona de Malabo II, reconocido por su arquitectura de vanguardia, estructuras sinuosas y modernos acabados de cristal, orientado a viajeros de negocios.",
            "city": "Malabo",
            "address": "Malabo II",
            "price_level": "alto",
            "stars": 5,
            "latitude": 3.7431,
            "longitude": 8.7618,
            "image": "imgns/hotel andachina.jpg",
        },
        {
            "name": "Hacienda Marcos Mbá Nguema",
            "description": "Complejo de agroturismo en Riaba, rodeado de cultivos, senderos y vegetación local para disfrutar de la naturaleza y la tranquilidad del sur de Bioko.",
            "city": "Riaba",
            "address": "La Granja de Riaba",
            "price_level": "medio",
            "stars": 3,
            "latitude": 3.3812,
            "longitude": 8.7516,
            "image": "imgns/playa de bioko.png",
        },
        {
            "name": "Grand Hotel Djibloho",
            "description": "Resort de 5 estrellas en la selva tropical de Djibloho, con centro de congresos, spa, suites, anfiteatro, campo de golf y propuestas de turismo ecológico.",
            "city": "Ciudad de la Paz",
            "address": "Provincia de Djibloho",
            "price_level": "alto",
            "stars": 5,
            "latitude": 1.5737,
            "longitude": 10.8256,
            "image": "imgns/hotel djiblho.jpg",
        },
        {
            "name": "Grand Hotel Bata",
            "description": "Complejo turístico de 15 plantas y 234 habitaciones frente al mar, con casino, discoteca, helipuerto, piscina exterior y restaurantes gourmet.",
            "city": "Bata",
            "address": "Frente al mar, Bata",
            "price_level": "alto",
            "stars": 5,
            "latitude": 1.8615,
            "longitude": 9.7540,
            "image": "imgns/h0tel bata.jpg",
        },
        {
            "name": "Hotel Panáfrica Boutique & Spa",
            "description": "Hotel boutique de 5 estrellas en el paseo marítimo de Bata, cerca de Playa Cocoteros, con atención personalizada, spa premium y vistas al Atlántico.",
            "city": "Bata",
            "address": "Paseo marítimo, Playa Cocoteros",
            "price_level": "alto",
            "stars": 5,
            "latitude": 1.8590,
            "longitude": 9.7512,
            "image": "imgns/hotel panafrica.jpg",
        },
    ]
    legacy_hotels = {"Hotel Moka", "Hotel del Golfo"}
    for hotel_data in hotel_catalog:
        item = Hotel.query.filter_by(name=hotel_data["name"]).first()
        if item is None:
            item = Hotel(**hotel_data)
            db.session.add(item)
        else:
            for key, value in hotel_data.items():
                setattr(item, key, value)
    for item in Hotel.query.filter(Hotel.name.in_(legacy_hotels)).all():
        db.session.delete(item)

    if NewsArticle.query.count() == 0:
        db.session.add_all(
            [
                NewsArticle(title="Memoria viva de Malabo", summary="Un recorrido por lugares y relatos que ayudan a entender la historia de la capital.", body="La historia de Guinea Ecuatorial también se conserva en sus calles, edificios, paisajes y relatos familiares. Esta sección reunirá contenidos para conocer ese patrimonio con respeto y contexto.", category="historia", image="default-news.svg"),
                NewsArticle(title="Agenda deportiva local", summary="Sigue la actualidad del deporte y las historias de quienes mueven el fútbol y otras disciplinas.", body="El deporte conecta barrios, ciudades y generaciones. Aquí compartiremos noticias, perfiles y eventos deportivos de Guinea Ecuatorial.", category="deporte", image="default-news.svg"),
                NewsArticle(title="Cultura y vida cotidiana", summary="Noticias sobre cultura, gastronomía, música y actividades de interés para la comunidad.", body="HOLA GUINEA reúne información práctica y contenidos de interés para residentes, visitantes y personas que quieren conocer mejor el país.", category="cultura", image="default-news.svg"),
            ]
        )

    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
