from django.conf.urls import patterns, include
from tastypie.api import Api
from .api import EntryResource, EntryTypeResource

v1_api = Api(api_name='v1')
v1_api.register(EntryResource())
v1_api.register(EntryTypeResource())


urlpatterns = patterns('',
    (r'^api/', include(v1_api.urls)),
)
