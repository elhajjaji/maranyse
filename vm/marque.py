"""MaranYSE — identité visuelle (logos, emblèmes et bannières de l'espace parents).

Les images sont chargées depuis le dossier d'assets (~/logo_web dans la VM ou ../container/logo_web dans le dépôt),
évitant d'embarquer ~760 Ko de base64 redondant dans le code Python.
"""
import base64
import os

_ICI = os.path.dirname(os.path.abspath(__file__))
_DOSSIERS = [
    os.path.join(_ICI, "logo_web"),
    os.path.join(os.path.expanduser("~"), "logo_web"),
    os.path.normpath(os.path.join(_ICI, "..", "container", "logo_web")),
]
# Image PNG 1×1 transparente de secours si un fichier est absent
_VIDE_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIAAAUAAeImBZsAAAAASUVORK5CYII=")


def _lire(rel):
    for d in _DOSSIERS:
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    return f.read()
            except OSError:
                pass
    return _VIDE_PNG


LOGO_PNG = _lire("logo4_440.png")
EMBLEME_PNG = _lire(os.path.join("web", "e320.png"))
EMBLEME_PETIT_PNG = _lire(os.path.join("web", "e128.png"))
LOGO_HD_JPG = _lire(os.path.join("web", "logo420.jpg"))
LOGO_PETIT_JPG = _lire(os.path.join("web", "logo200.jpg"))
TITRE_JPG = _lire(os.path.join("web", "ban440.jpg"))
SLOGAN_JPG = _lire(os.path.join("web", "slogan760.jpg"))
BANNIERE_JPG = _lire(os.path.join("web", "ban1200.jpg"))
FAVICON_PNG = _lire(os.path.join("web", "favjpeg.png"))
