import hashlib
import logging
import posixpath
import re
import time
from urllib.parse import unquote, urlparse

import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from forum.models import Imagen

log = logging.getLogger(__name__)

# Las 2527 imágenes ya migradas viven en `imagenes/<basename>`, donde el basename
# sale de la URL FINAL tras seguir redirecciones (archive.org devuelve a menudo
# otra captura: .../SWeQoFL.gif acabó como imagenes/9vqZ4rF.gif). Mantener el
# mismo esquema es lo que permite reanudar sin partir el bucket en dos rutas.
PREFIJO = "imagenes"
EXT_POR_TIPO = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
NOMBRE_LIMPIO = re.compile(r"[^A-Za-z0-9._-]")


def clave_r2(url_final, ext, img_id):
    """`imagenes/<basename saneado>`, con el id como red de seguridad."""
    base = posixpath.basename(unquote(urlparse(url_final).path))
    base = NOMBRE_LIMPIO.sub("_", base).lstrip(".")
    raiz, punto, _ = base.rpartition(".")
    if not punto or not raiz:
        base = f"{img_id}{ext}"
    return f"{PREFIJO}/{base}"

class Command(BaseCommand):
    help = "Download images from archive.org and upload to Cloudflare R2"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, help="Max images to process")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (archive.org rate limit)")
        parser.add_argument("--resume", action="store_true", help="Skip already-uploaded images")

    def handle(self, *args, **options):
        delay = options["delay"]
        limit = options.get("limit")
        resume = options.get("resume", False)

        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        domain = settings.AWS_S3_CUSTOM_DOMAIN

        qs = Imagen.objects.all()
        if resume:
            qs = qs.filter(descargada=False)
        if limit:
            qs = qs[:limit]

        total = qs.count()
        ok = fail = skip = 0
        start = time.time()

        self.stdout.write(f"Processing {total} images → R2 ({bucket})")

        for img in qs.iterator(chunk_size=50):
            subida = False
            for attempt in range(3):
                try:
                    r = requests.get(
                        img.url_original, timeout=30,
                        headers={"User-Agent": "ClashBangForum/1.0"},
                        allow_redirects=True,
                    )
                    if r.status_code != 200:
                        self.stdout.write(f"  [{img.id}] HTTP {r.status_code} (attempt {attempt+1})")
                        time.sleep(2 ** attempt)
                        continue

                    ct = r.headers.get("content-type", "image/png").split(";")[0].strip()
                    ext = EXT_POR_TIPO.get(ct, ".jpg")
                    key = clave_r2(r.url, ext, img.id)

                    # Muchos posts comparten los emoticonos del tema de SMF, así
                    # que el mismo basename se repite. Si el objeto ya está y el
                    # contenido coincide, se reutiliza; si no, desempata el hash.
                    digest = hashlib.md5(r.content).hexdigest()
                    existente = self._etag(client, bucket, key)
                    if existente == digest:
                        skip += 1
                    else:
                        if existente is not None:
                            raiz, _, sufijo = key.rpartition(".")
                            key = f"{raiz}-{digest[:8]}.{sufijo}"
                        client.put_object(
                            Bucket=bucket, Key=key, Body=r.content,
                            ContentType=ct, CacheControl="public, max-age=31536000, immutable",
                        )
                        ok += 1

                    r2_url = f"https://{domain}/{key}"
                    Imagen.objects.filter(id=img.id).update(url_r2=r2_url, descargada=True)
                    subida = True
                    hechas = ok + skip
                    if hechas % 20 == 0:
                        rate = hechas / ((time.time() - start) / 60)
                        self.stdout.write(f"  Progress: {hechas}/{total} ({rate:.0f}/min)")
                    break

                except (requests.Timeout, requests.ConnectionError) as e:
                    self.stdout.write(f"  [{img.id}] {e} (attempt {attempt+1})")
                    time.sleep(2 ** attempt)
                except Exception as e:
                    self.stdout.write(f"  [{img.id}] ERROR: {e}")
                    break

            if not subida:
                fail += 1
            time.sleep(delay)

        elapsed = time.time() - start
        self.stdout.write(self.style.SUCCESS(
            f"Done: {total} in {elapsed:.0f}s ({elapsed/60:.1f}min) | "
            f"OK {ok} | FAIL {fail} | SKIP {skip}"
        ))

    @staticmethod
    def _etag(client, bucket, key):
        """MD5 hex del objeto si existe (R2 devuelve el ETag entrecomillado)."""
        try:
            return client.head_object(Bucket=bucket, Key=key)["ETag"].strip('"')
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return None
            raise
