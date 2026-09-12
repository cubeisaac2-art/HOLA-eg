import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from models import db, DictionaryEntry, User

ENTRY_PATTERN = re.compile(
    r"^(?P<term>[^\t]+?)\s+(?:\d+(?:/\d+)?\s+)?(?:pref\.|ext\.)?\s*"
    r"(?P<marker>n\.|ad\. v\.|interj\.?|interr\.?|prep\.?|conj\.?|afirm\.?|neg\.?|indef\.?|num\.?|"
    r"pos\. pers\.?|in\. v\.|intrj\.?|intr\./tr\.?|3\.ª pers\./sing\.)\s+(?P<meaning>.+)$",
    re.IGNORECASE,
)


def parse_entries(source_path):
    entries = []
    seen = set()
    for raw_line in Path(source_path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("DICCIONARIO", "(", "Fuente:", "=", "SECCIÓN", "NOTA:")):
            continue
        match = ENTRY_PATTERN.match(line)
        if not match:
            continue
        term = re.sub(r"^[¹²'\"*]+|[¹²'\"*]+$", "", match.group("term")).strip(" ,")
        meaning = match.group("meaning").split(";", 1)[0].strip()
        meaning = re.sub(r"\s+", " ", meaning)
        if len(term) < 1 or len(term) > 120 or not meaning or len(meaning) > 180:
            continue
        key = (term.casefold(), meaning.casefold())
        if key not in seen:
            seen.add(key)
            entries.append((term, meaning))
    return entries


def import_entries(source_path):
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(email="admin@holaguinea.com").first()
        if admin is None:
            raise RuntimeError("No existe admin@holaguinea.com; inicia la aplicación una vez para crearla.")
        parsed = parse_entries(source_path)
        added = 0
        for term, translation in parsed:
            exists = DictionaryEntry.query.filter_by(term=term, translation=translation, language="fang").first()
            if exists:
                continue
            db.session.add(DictionaryEntry(
                term=term,
                translation=translation,
                language="fang",
                category="general",
                notes="Importado de la sección Fang-Español, letra A.",
                created_by_id=admin.id,
            ))
            added += 1
        db.session.commit()
        print(f"parsed={len(parsed)} added={added} total_fang={DictionaryEntry.query.filter_by(language='fang').count()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python scripts/import_fang_dictionary.py <archivo.txt>")
    import_entries(sys.argv[1])
