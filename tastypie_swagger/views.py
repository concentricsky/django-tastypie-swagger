import sys
import json

from django.views.generic import TemplateView
from django.http import HttpResponse, Http404
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.conf import settings

from .mapping import ResourceSwaggerMapping


class TastypieApiMixin(object):
    """
    Provides views with a 'tastypie_api' attr representing a tastypie.api.Api instance

    Python path must be defined in settings as TASTYPIE_SWAGGER_API_MODULE
    """
    def __init__(self, *args, **kwargs):
        super(TastypieApiMixin, self).__init__(*args, **kwargs)
        tastypie_api_module = getattr(settings, 'TASTYPIE_SWAGGER_API_MODULE', None)
        if not tastypie_api_module:
            raise ImproperlyConfigured("Must define TASTYPIE_SWAGGER_API_MODULE in settings as path to a tastypie.api.Api instance")
        path, attr = tastypie_api_module.rsplit('.', 1)
        try:
            tastypie_api = getattr(sys.modules[path], attr, None)
        except KeyError:
            raise ImproperlyConfigured("%s is not a valid python path" % path)
        if not tastypie_api:
            raise ImproperlyConfigured("%s is not a valid tastypie.api.Api instance" % tastypie_api_module)
        self.tastypie_api = tastypie_api


class SwaggerApiDataMixin(object):
    """
    Provides required API context data
    """

    def get_context_data(self, *args, **kwargs):
        context = super(SwaggerApiDataMixin, self).get_context_data(*args, **kwargs)
        context.update({
            # TODO: How should versions be controlled?
            'apiVersion': '0.1',
            'swaggerVersion': '1.1',
        })
        return context


class JSONView(TemplateView):
    """
    Simple JSON rendering
    """
    response_class = HttpResponse

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response with a template rendered with the given context.
        """
        for k in ['params','view']:
            if k in context:
                del context[k]
        return self.response_class(
            json.dumps(context),
            content_type='application/json',
            **response_kwargs
        )


class SwaggerView(TastypieApiMixin, TemplateView):
    """
    Display the swagger-ui page
    """

    template_name = 'tastypie_swagger/index.html'


class ResourcesView(TastypieApiMixin, SwaggerApiDataMixin, JSONView):
    """
    Provide a top-level resource listing for swagger

    This JSON must conform to https://github.com/wordnik/swagger-core/wiki/Resource-Listing
    """

    def get_context_data(self, *args, **kwargs):
        context = super(ResourcesView, self).get_context_data(*args, **kwargs)

        # Construct schema endpoints from resources
        apis = [{'path': '/%s' % name} for name in sorted(self.tastypie_api._registry.keys())]
        context.update({
            'basePath': self.request.build_absolute_uri(reverse('tastypie_swagger:schema')),
            'apis': apis,
        })
        return context


class SchemaView(TastypieApiMixin, SwaggerApiDataMixin, JSONView):
    """
    Provide an individual resource schema for swagger

    This JSON must conform to https://github.com/wordnik/swagger-core/wiki/API-Declaration
    """

    def get_context_data(self, *args, **kwargs):
        # Verify matching tastypie resource exists
        resource_name = kwargs.get('resource', None)
        if not resource_name in self.tastypie_api._registry:
            raise Http404

        # Generate mapping from tastypie.resources.Resource.build_schema
        resource = self.tastypie_api._registry.get(resource_name)
        mapping = ResourceSwaggerMapping(resource)

        context = super(SchemaView, self).get_context_data(*args, **kwargs)
        context.update({
            'basePath': '/',
            'apis': mapping.build_apis(),
            'models': mapping.build_models()
        })
        return context
