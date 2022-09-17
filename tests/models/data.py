from django.db import models


__all__ = ('NameValue',)


class NameValue(models.Model):
    name = models.CharField(max_length=32)
    value = models.IntegerField()


