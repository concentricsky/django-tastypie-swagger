try:
    from django.conf.urls import url
except ImportError:
    from django.conf.urls.defaults import url

try:
    from django.conf.urls import patterns
except ImportError:
    try:
        from django.conf.urls.defaults import patterns
    except ImportError:

        def patterns(name, *args):
            return args


from .views import SwaggerView, ResourcesView, SchemaView

urlpatterns = patterns(
    '',
    url(r'^$', SwaggerView.as_view(), name='index'),
    url(r'^resources/$', ResourcesView.as_view(), name='resources'),
    url(r'^schema/(?P<resource>\S+)$', SchemaView.as_view()),
    url(r'^schema/$', SchemaView.as_view(), name='schema'),
)
