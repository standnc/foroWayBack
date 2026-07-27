import os
import sqlite3
import sys
from datetime import datetime

from django.core.management.base import BaseCommand

from forum.models import Categoria, Hilo, Imagen, Post


def parse_fecha(texto):
    if not texto or texto == "0000-00-00":
        return None
    texto = texto.strip()
    for f in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, f)
        except ValueError:
            continue
    return datetime(2009, 1, 1)

class Command(BaseCommand):
    help = "Migra datos de SQLite (foro.db) a PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument("--sqlite", default="/var/www/foroWayBack/foro.db")

    def handle(self, *args, **options):
        db_path = options["sqlite"]
        if not os.path.exists(db_path):
            self.stderr.write(f"ERROR: no encuentra {db_path}")
            sys.exit(1)

        self.stdout.write(f"Conectando a SQLite: {db_path}")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 1. Categorías
        self.stdout.write("\n--- Categorías ---")
        cur.execute("SELECT id, slug, nombre FROM categorias ORDER BY id")
        c = 0
        for row in cur.fetchall():
            Categoria.objects.update_or_create(
                id_original=row[0],
                defaults={"slug": row[1], "nombre": row[2]},
            )
            c += 1
        self.stdout.write(f"  {c} categorías")

        # 2. Hilos
        self.stdout.write("\n--- Hilos ---")
        cur.execute("SELECT id, categoria_id, titulo, url_original, archivo_html, num_posts, fecha_creado FROM hilos ORDER BY id")
        c = 0
        for row in cur.fetchall():
            cat = Categoria.objects.filter(id_original=row[1]).first()
            if not cat:
                self.stderr.write(f"  Salto hilo {row[0]}: categoria {row[1]} no encontrada")
                continue
            fecha = parse_fecha(row[6])
            slug = row[2].lower().replace(" ", "-").replace("/", "-")[:250] if row[2] else f"hilo-{row[0]}"
            Hilo.objects.update_or_create(
                id_original=row[0],
                defaults={
                    "categoria": cat,
                    "titulo": row[2] or "Sin título",
                    "slug": slug,
                    "url_original": row[3] or "",
                    "archivo_html": row[4] or "",
                    "num_posts": row[5] or 0,
                    "creado": fecha or datetime(2009, 1, 1),
                    "ultimo_post": fecha,
                    "es_historico": True,
                },
            )
            c += 1
        self.stdout.write(f"  {c} hilos")

        # 3. Posts
        self.stdout.write("\n--- Posts ---")
        cur.execute("SELECT id, hilo_id, msg_id, autor, fecha, contenido, orden FROM posts ORDER BY id")
        c = 0
        for row in cur.fetchall():
            h = Hilo.objects.filter(id_original=row[1]).first()
            if not h:
                continue
            fecha = parse_fecha(row[4])
            Post.objects.update_or_create(
                id_original=row[0],
                defaults={
                    "hilo": h,
                    "autor_historico": row[3] or "",
                    "msg_id": row[2] or "",
                    "contenido": row[5] or "",
                    "creado": fecha or datetime(2009, 1, 1),
                    "orden": row[6] or 0,
                    "es_historico": True,
                },
            )
            c += 1
        self.stdout.write(f"  {c} posts")

        # 4. Imágenes
        self.stdout.write("\n--- Imágenes ---")
        cur.execute("SELECT id, post_id, url_original FROM imagenes ORDER BY id")
        c = 0
        for row in cur.fetchall():
            p = Post.objects.filter(id_original=row[1]).first() if row[1] else None
            if not p:
                continue
            Imagen.objects.update_or_create(
                id_original=row[0],
                defaults={"post": p, "url_original": row[2] or ""},
            )
            c += 1
        self.stdout.write(f"  {c} imágenes")

        conn.close()
        self.stdout.write("\n✅ Migración completada")
