try:
	from django.conf.urls import patterns, include, url
except ImportError:
	from django.conf.urls.defaults import patterns, include, url

from .views import SwaggerView, ResourcesView, SchemaView

urlpatterns = patterns('',
    url(r'^$', SwaggerView.as_view(), name='index'),
    url(r'^api-docs/$', ResourcesView.as_view(), name='api-docs'),
    url(r'^schema/(?P<resource>\S+)/$', SchemaView.as_view(), name='resources_schema'),
    url(r'^schema/$', SchemaView.as_view(), name='schema'),
)
