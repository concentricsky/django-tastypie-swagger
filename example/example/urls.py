from django.conf.urls import include, url
from django.contrib import admin
from demo.apis import api

urlpatterns = [
    url(r'^api/', include(api.urls)),
    url(r'^api/doc/', include(('tastypie_swagger.urls', 'tastypie_swagger'),
                              namespace='demo_api_swagger'),
      kwargs={
          "tastypie_api_module":"demo.apis.api",
          "namespace":"demo_api_swagger",
          "version": "0.1"}
    ),
    url(r'^admin/', admin.site.urls),
]
