from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, FileField as WtFormsFileField, FloatField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    email = StringField("Correo", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Entrar")


class RegisterForm(FlaskForm):
    full_name = StringField("Nombre completo", validators=[DataRequired(), Length(min=2, max=120)])
    username = StringField("Usuario", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Correo", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Crear cuenta")


class ProfileForm(FlaskForm):
    full_name = StringField("Nombre completo", validators=[DataRequired(), Length(min=2, max=120)])
    username = StringField("Usuario", validators=[DataRequired(), Length(min=3, max=80)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=500)])
    profile_image = FileField("Foto de perfil", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo se permiten imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Guardar perfil")


class DictionaryForm(FlaskForm):
    term = StringField("Término", validators=[DataRequired(), Length(min=1, max=120)])
    translation = StringField("Traducción", validators=[DataRequired(), Length(min=1, max=180)])
    language = SelectField("Lengua", choices=[("fang", "Fang"), ("bubi", "Bubi"), ("ndowe", "Ndowe"), ("annobonense", "Annobonense"), ("kombe", "Kombe"), ("benga", "Benga"), ("baseke", "Baseke"), ("fang-ntumu", "Fang-Ntumu"), ("otra", "Otra")], validators=[DataRequired()])
    category = SelectField("Categoría", choices=[("general", "General"), ("saludo", "Saludo"), ("comida", "Comida"), ("naturaleza", "Naturaleza"), ("cultura", "Cultura")], default="general")
    notes = TextAreaField("Notas", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Guardar")


class FoodForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(min=2, max=150)])
    description = TextAreaField("Descripción", validators=[DataRequired()])
    city = StringField("Ciudad", validators=[DataRequired(), Length(min=2, max=80)])
    price_level = SelectField("Precio", choices=[("bajo", "Bajo"), ("medio", "Medio"), ("alto", "Alto")], default="medio")
    category = SelectField("Tipo", choices=[("local", "Local"), ("marino", "Marino"), ("vegetariano", "Vegetariano"), ("postre", "Postre")], default="local")
    image = FileField("Imagen", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Guardar")


class RestaurantForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(min=2, max=150)])
    description = TextAreaField("Descripción", validators=[DataRequired()])
    city = StringField("Ciudad", validators=[DataRequired(), Length(min=2, max=80)])
    address = StringField("Dirección", validators=[Optional(), Length(max=200)])
    phone = StringField("Teléfono", validators=[Optional(), Length(max=50)])
    whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=50)])
    price_level = SelectField("Precio", choices=[("bajo", "Bajo"), ("medio", "Medio"), ("alto", "Alto")], default="medio")
    stars = IntegerField("Estrellas", validators=[Optional(), NumberRange(min=1, max=5)])
    latitude = FloatField("Latitud", validators=[DataRequired()])
    longitude = FloatField("Longitud", validators=[DataRequired()])
    image = FileField("Imagen", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Guardar")


class HotelForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(min=2, max=150)])
    description = TextAreaField("Descripción", validators=[DataRequired()])
    city = StringField("Ciudad", validators=[DataRequired(), Length(min=2, max=80)])
    address = StringField("Dirección", validators=[Optional(), Length(max=200)])
    phone = StringField("Teléfono", validators=[Optional(), Length(max=50)])
    website = StringField("Sitio web", validators=[Optional(), Length(max=200)])
    price_level = SelectField("Precio", choices=[("bajo", "Bajo"), ("medio", "Medio"), ("alto", "Alto")], default="medio")
    stars = IntegerField("Estrellas", validators=[Optional(), NumberRange(min=1, max=5)])
    latitude = FloatField("Latitud", validators=[DataRequired()])
    longitude = FloatField("Longitud", validators=[DataRequired()])
    image = FileField("Imagen", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Guardar")


class PlaceRecommendationForm(FlaskForm):
    name = StringField("Nombre del sitio", validators=[DataRequired(), Length(min=2, max=150)])
    description = TextAreaField("¿Por qué lo recomiendas?", validators=[DataRequired(), Length(min=10, max=1000)])
    city = StringField("Ciudad o zona", validators=[DataRequired(), Length(min=2, max=80)])
    category = SelectField("Categoría", choices=[("naturaleza", "Naturaleza"), ("cultura", "Cultura"), ("historia", "Historia"), ("deporte", "Deporte"), ("ocio", "Ocio")], default="cultura")
    address = StringField("Dirección o referencia", validators=[Optional(), Length(max=200)])
    latitude = FloatField("Latitud", validators=[Optional()])
    longitude = FloatField("Longitud", validators=[Optional()])
    image = FileField("Imagen", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Enviar recomendación")


class NewsForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(min=5, max=180)])
    summary = StringField("Resumen", validators=[DataRequired(), Length(min=10, max=300)])
    body = TextAreaField("Contenido", validators=[DataRequired(), Length(min=20, max=5000)])
    category = SelectField("Categoría", choices=[("actualidad", "Actualidad"), ("historia", "Historia"), ("deporte", "Deporte"), ("cultura", "Cultura")], default="actualidad")
    source_url = StringField("Enlace de fuente", validators=[Optional(), Length(max=500)])
    image = FileField("Imagen", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Publicar noticia")


class ReviewForm(FlaskForm):
    rating = IntegerField("Valoración", validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField("Comentario", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Enviar valoración")


class NotificationForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(min=2, max=180)])
    body = TextAreaField("Mensaje", validators=[DataRequired(), Length(min=5, max=500)])
    target_scope = SelectField("Destino", choices=[("all", "Todos"), ("user", "Usuario específico")], default="all")
    target_user_id = IntegerField("ID del usuario", validators=[Optional()])
    submit = SubmitField("Enviar notificación")
