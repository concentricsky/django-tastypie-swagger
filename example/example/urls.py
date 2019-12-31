from django.conf.urls import patterns, include, url
from django.contrib import admin
from demo.apis import api

urlpatterns = patterns('',
    url(r'^api/', include(api.urls)),
    url(r'^api/doc/', include('tastypie_swagger.urls', 
                              namespace='demo_api_swagger'),
      kwargs={
          "tastypie_api_module":"demo.apis.api",
          "namespace":"demo_api_swagger",
          "version": "0.1"}
    ),
    url(r'^admin/', include(admin.site.urls)),
)
