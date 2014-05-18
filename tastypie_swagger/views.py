import sys
import json

from django.conf import settings
from django.views.generic import TemplateView
from django.http import HttpResponse, Http404
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

import tastypie

from .mapping import ResourceSwaggerMapping


class TastypieApiMixin(object):
    """
    Provides views with a 'tastypie_api' attr representing a tastypie.api.Api instance

    Python path must be defined in settings as TASTYPIE_SWAGGER_API_MODULE
    """
    _tastypie_api = None

    @property
    def tastypie_api(self):

        if not self._tastypie_api:

            tastypie_api_module = self.kwargs.get('tastypie_api_module', None)
            if not tastypie_api_module:
                raise ImproperlyConfigured("tastypie_api_module must be defined as an extra parameters in urls.py with its value being a path to a tastypie.api.Api instance.")

            if isinstance(tastypie_api_module, tastypie.api.Api):
                tastypie_api = tastypie_api_module
            else:
                path, attr = tastypie_api_module.rsplit('.', 1)
                try:
                    tastypie_api = getattr(sys.modules[path], attr, None)
                except KeyError:
                    raise ImproperlyConfigured("%s is not a valid python path" % path)
                if not tastypie_api:
                    raise ImproperlyConfigured("%s is not a valid tastypie.api.Api instance" % tastypie_api_module)

            self._tastypie_api = tastypie_api

        return self._tastypie_api

class SwaggerApiDataMixin(object):
    """
    Provides required API context data
    """

    def generate_api_info(self):
        return {
            'title': settings.TASTYPIE_SWAGGER_SETTINGS.get('title', ''),
            'description': settings.TASTYPIE_SWAGGER_SETTINGS.get('description', ''),
            'termsOfServiceUrl': settings.TASTYPIE_SWAGGER_SETTINGS.get('terms_of_service_url', ''),
            'contact': settings.TASTYPIE_SWAGGER_SETTINGS.get('contact', ''),
            'license': settings.TASTYPIE_SWAGGER_SETTINGS.get('license', ''),
            'licenseUrl': settings.TASTYPIE_SWAGGER_SETTINGS.get('license_url', ''),
        }

    def get_context_data(self, *args, **kwargs):
        from . import SWAGGER_VERSION
        context = super(SwaggerApiDataMixin, self).get_context_data(*args, **kwargs)
        context.update({
            'apiVersion': self.kwargs.get('api_version', '0.1'),
            'swaggerVersion': SWAGGER_VERSION,
            'logo_url': settings.TASTYPIE_SWAGGER_SETTINGS.get('LOGO_URL', )
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

        # This cannot be serialized if it is a api instance and we don't need it anyway.
        context.pop('tastypie_api_module')

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

    def get_context_data(self, **kwargs):
        context = super(SwaggerView, self).get_context_data(**kwargs)

        context.update({
            'api_docs_url' : reverse('%s:api-docs' % self.kwargs.get('namespace')),
            'app_name': settings.TASTYPIE_SWAGGER_SETTINGS.get('app_name', 'swagger'),
            'logo_url': settings.TASTYPIE_SWAGGER_SETTINGS.get('logo_url', None),
            'app_url': settings.TASTYPIE_SWAGGER_SETTINGS.get('app_url', ''), #TODO Make sure the default is ok
            'show_swagger_demo_icons': settings.TASTYPIE_SWAGGER_SETTINGS.get('show_swagger_demo_icons', False),
            'supported_submit_methods': json.dumps(settings.TASTYPIE_SWAGGER_SETTINGS.get('supported_submit_methods',
                                                                                      ['get','post','put','delete'])),
            'doc_expansion': settings.TASTYPIE_SWAGGER_SETTINGS.get('doc_expansion', 'none'),
            'boolean_values': json.dumps(settings.TASTYPIE_SWAGGER_SETTINGS.get('boolean_values', [True, False])),
            'use_minimized_js': settings.TASTYPIE_SWAGGER_SETTINGS.get('use_minimized_js', False)
        })

        return context


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
            # We remove last char as it should be a /, not really reliable but will make it for now.
            'basePath': self.request.build_absolute_uri(reverse('%s:schema' % self.kwargs.get('namespace')))[:-1],
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
            'basePath': self.request.build_absolute_uri(
                    reverse(
                        'api_{}_top_level'.format(self.tastypie_api.api_name),
                        kwargs={'api_name': self.tastypie_api.api_name}
                    )
                )[:-1],#TODO find a better way to remove the trailing slash
            'resourcePath': '/{}'.format(resource_name),
            #TODO deal with this as next step, the path attribute should be fixed.
            'apis': mapping.build_apis(),
            'models': mapping.build_models()
        })
        return context
