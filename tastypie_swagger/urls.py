from django import __version__ as django_version
try:
	from django.conf.urls import patterns, include, url
except ImportError:
	from django.conf.urls.defaults import patterns, include, url

from .views import SwaggerView, ResourcesView, SchemaView

django_version = django_version.split('.')
main_ver = int(django_version)[0]
secondary_ver = int(django_version)[1]

if main_ver == 1 and secondary_ver < 9:
	urlpatterns = patterns('',
	    url(r'^$', SwaggerView.as_view(), name='index'),
	    url(r'^resources/$', ResourcesView.as_view(), name='resources'),
	    url(r'^schema/(?P<resource>\S+)$', SchemaView.as_view()),
	    url(r'^schema/$', SchemaView.as_view(), name='schema'),
	)
else:
	# RemovedInDjango110Warning: 
	# django.conf.urls.patterns() is deprecated and will be removed in Django 1.10. 
	# Update your urlpatterns to be a list of django.conf.urls.url() instances instead.
	urlpatterns = [
	    url(r'^$', SwaggerView.as_view(), name='index'),
	    url(r'^resources/$', ResourcesView.as_view(), name='resources'),
	    url(r'^schema/(?P<resource>\S+)$', SchemaView.as_view()),
	    url(r'^schema/$', SchemaView.as_view(), name='schema')
	]
