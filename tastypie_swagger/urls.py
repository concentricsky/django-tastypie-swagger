from .views import SwaggerView, ResourcesView, SchemaView
from tastypie_swagger.views import SwaggerSpecs2View

from django.conf.urls import url

urlpatterns = [
    url(r'^$', SwaggerView.as_view(), name='index'),
    url(r'^resources/$', ResourcesView.as_view(), name='resources'),
    url(r'^specs/(swagger.json)?$', SwaggerSpecs2View.as_view(), name='specs'),
    url(r'^schema/(?P<resource>\S+)/$', SchemaView.as_view()),
    url(r'^schema/$', SchemaView.as_view(), name='schema'),
]
