import logging
import time

import boto3
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from forum.models import Imagen

log = logging.getLogger(__name__)

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

                    ct = r.headers.get("content-type", "image/png")
                    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}.get(ct, ".jpg")
                    key = f"media/public/imagenes/{img.id}{ext}"

                    client.put_object(
                        Bucket=bucket, Key=key, Body=r.content,
                        ContentType=ct, CacheControl="public, max-age=31536000, immutable",
                    )

                    r2_url = f"https://{domain}/{key}"
                    Imagen.objects.filter(id=img.id).update(url_r2=r2_url, descargada=True)
                    ok += 1
                    if ok % 20 == 0:
                        rate = ok / ((time.time() - start) / 60)
                        self.stdout.write(f"  Progress: {ok}/{total} OK ({rate:.0f}/min)")
                    break

                except (requests.Timeout, requests.ConnectionError) as e:
                    self.stdout.write(f"  [{img.id}] {e} (attempt {attempt+1})")
                    time.sleep(2 ** attempt)
                except Exception as e:
                    self.stdout.write(f"  [{img.id}] ERROR: {e}")
                    fail += 1
                    break

            time.sleep(delay)

        elapsed = time.time() - start
        self.stdout.write(self.style.SUCCESS(
            f"Done: {total} in {elapsed:.0f}s ({elapsed/60:.1f}min) | "
            f"OK {ok} | FAIL {fail} | SKIP {skip}"
        ))
