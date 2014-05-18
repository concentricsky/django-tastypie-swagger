from tastypie import fields
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from .models import Entry, EntryType, EntryWithCharId


class EntryTypeResource(ModelResource):
    entries = fields.ToManyField('test_app.api.EntryResource', 'entry_set')
    class Meta:
        queryset = EntryType.objects.all()
        filtering = {
            "entries": ALL_WITH_RELATIONS,
        }

class EntryResource(ModelResource):
    parent = fields.ToOneField('test_app.api.EntryResource',
        'parent', null=True)
    type = fields.ToOneField('test_app.api.EntryTypeResource', 'type')
    class Meta:
        queryset = Entry.objects.all()
        filtering = {
            "title": ALL ,
            "parent": ALL_WITH_RELATIONS,
            "type": ALL_WITH_RELATIONS,
        }
        extra_actions = [
            {
                "name": "search",
                "http_method": "GET",
                "resource_type": "list",
                "description": "Seach endpoint",
                "fields": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Search query terms"
                    }
                }
            }
        ]

class EntryWithCharIdResource(ModelResource):
    parent = fields.ToOneField('test_app.api.EntryWithCharIdResource',
        'parent', null=True)
    type = fields.ToOneField('test_app.api.EntryTypeResource', 'type')
    class Meta:
        queryset = EntryWithCharId.objects.all()
        filtering = {
            "title": ALL ,
            "parent": ALL_WITH_RELATIONS,
            "type": ALL_WITH_RELATIONS,
        }