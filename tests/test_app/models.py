from django.db import models

class Entry(models.Model):
    title = models.CharField(max_length=64, blank=True, null=True)
    parent = models.ForeignKey('Entry', null=True, blank=True)
    type = models.ForeignKey('EntryType', null=True, blank=True)

class EntryType(models.Model):
    name = models.CharField(max_length=64, blank=True, null=True)

class EntryWithCharId(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    title = models.CharField(max_length=64, blank=True, null=True)
    parent = models.ForeignKey('Entry', null=True, blank=True)
    type = models.ForeignKey('EntryType', null=True, blank=True)
