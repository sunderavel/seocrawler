from django.db import models

from core.constants import TRUE, ZERO
from core.model_choices import CRAWL_PAGE_STATUS

# Create your models here.
class Domain(models.Model):
    domain_name = models.CharField(max_length=255, unique=TRUE, db_index=TRUE, null=TRUE)
    created_at = models.DateTimeField(auto_now_add=TRUE)


class Page(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="pages", null=TRUE)
    url = models.URLField(unique=TRUE, null=TRUE)
    status_code = models.IntegerField(choices=CRAWL_PAGE_STATUS, default=ZERO)
    crawled_at = models.DateTimeField(auto_now_add=TRUE)

    class Meta:
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["status_code"]),
        ]


class Insight(models.Model):
    page = models.OneToOneField(Page, on_delete=models.CASCADE, primary_key=TRUE)
    title = models.CharField(max_length=255, null=TRUE, blank=TRUE)
    meta_description = models.TextField(null=TRUE, blank=TRUE)

    h1 = models.JSONField(default=list)
    h2 = models.JSONField(default=list)
    h3 = models.JSONField(default=list)

    p_count = models.IntegerField(default=ZERO)
    image_count = models.IntegerField(default=ZERO)

    internal_links = models.IntegerField(default=ZERO)
    external_links = models.IntegerField(default=ZERO)

    keywords = models.JSONField(default=list)
    
    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["image_count"]),
            models.Index(fields=["internal_links"]),
        ]