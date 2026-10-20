from django.db import models

class Run(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    mode = models.CharField(max_length=20)
    summary = models.JSONField()
    cases = models.JSONField()
