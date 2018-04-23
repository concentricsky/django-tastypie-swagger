from django.conf.urls import url


from .views import SwaggerView, ResourcesView, SchemaView

urlpatterns = [
    url(r'^$', SwaggerView.as_view(), name='index'),
    url(r'^resources/$', ResourcesView.as_view(), name='resources'),
    url(r'^schema/(?P<resource>\S+)/$', SchemaView.as_view()),
    url(r'^schema/$', SchemaView.as_view(), name='schema'),
]
