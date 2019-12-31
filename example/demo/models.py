from django.db import models
from django.db.models import fields


class FooModel(models.Model):
    text = fields.CharField(max_length=100, default='', null=True,
                            help_text='Text for foo')


class BarModel(models.Model):
    text = fields.CharField(max_length=100, default='', null=True,
                            help_text='Text for bar')
