from flask import Blueprint, render_template, request, redirect
from repositories.post_repo import obtener_feed, obtener_feed_con_paginacion, contar_posts

feed_bp = Blueprint("feed", __name__)

@feed_bp.route('/')
def home():
    return redirect('/feed')

@feed_bp.route('/feed')
def ver_feed():
    try:
        pagina = int(request.args.get("page", 1))
        por_pagina = 10
        offset = (pagina - 1) * por_pagina

        total_posts = contar_posts()
        total_paginas = (total_posts + por_pagina - 1) // por_pagina
        posts = obtener_feed_con_paginacion(limit=por_pagina, offset=offset)

        return render_template("feed.html", posts=posts, pagina=pagina, total_paginas=total_paginas)
    except Exception as e:
        print("[ERROR en paginación /feed]:", e)
        return render_template("feed.html", posts=[], pagina=1, total_paginas=1, error="Error cargando el feed.")

@feed_bp.route('/feed_fragment')
def feed_fragment():
    try:
        desde = request.args.get("desde")
        posts = obtener_feed(limit=10, desde=desde)
        if not posts:
            return ""
        return render_template("partials/feed_items.html", posts=posts)
    except Exception as e:
        print("[ERROR en feed_fragment]:", e)
        return ""