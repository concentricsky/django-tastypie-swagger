from django.conf.urls import patterns, include, url

from django.contrib import admin
from test_app import urls as test_app_urls

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'swagger_dev.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'', include(test_app_urls)),
    url(r'api/v1/doc/',
      include('tastypie_swagger.urls', namespace='tastypie_swagger'),
      kwargs={"tastypie_api_module":test_app_urls.v1_api, "namespace":"tastypie_swagger"}
    ),
)
