from .views import SwaggerView, ResourcesView, SchemaView
try:
    from django.conf.urls import include, url

    urlpatterns = [
        url(r'^$', SwaggerView.as_view(), name='index'),
        url(r'^resources/$', ResourcesView.as_view(), name='resources'),
        url(r'^schema/(?P<resource>\S+)$', SchemaView.as_view()),
        url(r'^schema/$', SchemaView.as_view(), name='schema'),
    ]
except ImportError:
    from django.conf.urls.defaults import patterns, include, url

    urlpatterns = patterns('',
        url(r'^$', SwaggerView.as_view(), name='index'),
        url(r'^resources/$', ResourcesView.as_view(), name='resources'),
        url(r'^schema/(?P<resource>\S+)$', SchemaView.as_view()),
        url(r'^schema/$', SchemaView.as_view(), name='schema'),
    )

