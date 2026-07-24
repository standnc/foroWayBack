from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """CSS, JS, fuentes — público, cacheable, sin signed URLs."""
    location = "static"
    default_acl = "public-read"
    querystring_auth = False
    file_overwrite = True


class PublicMediaStorage(S3Boto3Storage):
    """Avatares, imágenes del foro — público, sin colisiones de nombre."""
    location = "media/public"
    default_acl = "public-read"
    file_overwrite = False
    querystring_auth = False


class PrivateMediaStorage(S3Boto3Storage):
    """Adjuntos privados — signed URLs, nunca por CDN público."""
    location = "media/private"
    default_acl = "private"
    file_overwrite = False
    querystring_auth = True
    custom_domain = False
