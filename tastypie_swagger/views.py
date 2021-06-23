from importlib import import_module
import json
import sys
from tastypie_swagger.mapping import ResourceSwaggerMapping

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.http import HttpResponse, Http404
from django.views.generic import TemplateView
import tastypie

from tastypie_swagger.mapping2 import ResourceSwagger2Mapping


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
                raise ImproperlyConfigured(
                    "tastypie_api_module must be defined as an extra parameters in urls.py with its value being a path to a tastypie.api.Api instance.")

            if isinstance(tastypie_api_module, tastypie.api.Api):
                tastypie_api = tastypie_api_module
            else:
                path, attr = tastypie_api_module.rsplit('.', 1)
                try:
                    tastypie_api = getattr(import_module(path), attr, None)
                except KeyError:
                    raise ImproperlyConfigured(
                        "%s is not a valid python path" % path)
                if not tastypie_api:
                    raise ImproperlyConfigured(
                        "%s is not a valid tastypie.api.Api instance" % tastypie_api_module)

            self._tastypie_api = tastypie_api

        return self._tastypie_api


class SwaggerApiDataMixin(object):

    """
    Provides required API context data
    """

    def get_context_data(self, *args, **kwargs):
        context = super(SwaggerApiDataMixin, self).get_context_data(
            *args, **kwargs)
        context.update({
            'apiVersion': self.kwargs.get('version', 'Unknown'),
            'swaggerVersion': '1.2',
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

        # This cannot be serialized if it is a api instance and we don't need
        # it anyway.
        context.pop('tastypie_api_module', None)

        for k in ['params', 'view']:
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
        context['discovery_url'] = reverse(
            '%s:resources' % self.kwargs.get('namespace'))
        return context


class ResourcesView(TastypieApiMixin, SwaggerApiDataMixin, JSONView):

    """
    Provide a top-level resource listing for swagger

    This JSON must conform to https://github.com/wordnik/swagger-core/wiki/Resource-Listing
    """

    def get_context_data(self, *args, **kwargs):
        context = super(ResourcesView, self).get_context_data(*args, **kwargs)

        # Construct schema endpoints from resources
        apis = [{'path': '/%s' % name}
                for name in sorted(self.tastypie_api._registry.keys())]
        context.update({
            'basePath': self.request.build_absolute_uri(reverse('%s:schema' % self.kwargs.get('namespace'))).rstrip('/'),
            'apis': apis,
        })
        return context


class Schema2View(TastypieApiMixin, SwaggerApiDataMixin, JSONView):

    """
    Provide an individual resource schema for swagger

    This JSON must conform to http://swagger.io/specification/
    at Version 2.0

    For testing see example/demo.tests, which validates a default ModelResource
    to conform to this specification
    """

    def get_context_data(self, *args, **kwargs):
        # Verify matching tastypie resource exists
        resource_name = kwargs.get('resource', None)
        if not resource_name in self.tastypie_api._registry:
            raise Http404

        # Generate mapping from tastypie.resources.Resource.build_schema
        resource = self.tastypie_api._registry.get(resource_name)
        mapping = ResourceSwagger2Mapping(resource)

        context = super(SchemaView, self).get_context_data(*args, **kwargs)
        context.update({
            'basePath': '/',
            'apis': mapping.build_apis(),
            'models': mapping.build_models(),
            'resourcePath': '/{0}'.format(resource._meta.resource_name)
        })
        return context


class SwaggerSpecs2View(TastypieApiMixin, JSONView):

    """
    Provide a top-level resource listing for swagger

    This JSON must conform to https://github.com/wordnik/swagger-core/wiki/Resource-Listing

    Usage:
        url(r'^api/doc/', include('tastypie_swagger.urls',
                              namespace='demo_api_swagger'),
          kwargs={
              "tastypie_api_module":"demo.apis.api",
              "namespace":"demo_api_swagger",
              "version": "0.1"}
        ),

    This sets up the api/doc/specs/swagger.json URI (along with the V1 URIs)
    to return Swagger V2 compliant JSON.

    Note that your Api instance may contain several attributes that are
    processed by SwaggerSpecs2View:

    api.title - string, defaults to api_name
    api.description - string, defaults to api_name
    api.version - string, defaults to '1.0'
    api.basePath - string of common base URI. if not provided defaults to the
    api's first Resource base path

    In addition you may override any of the 'info' attributes in the
    specification by adding an api.meta dict, e.g.

    api.info = {
        'title' : 'some title',
        'license': {
           'name': 'commerical',
           'URL': 'http://example.com/api/license.html',
        }
    }

    Note that 'path' and 'definitions' values of the output JSON are produced
    by mapping the Swagger V1 output to V2 syntax. Thus any V2 specifics are
    not yet supported.
    """

    def get_resource(self, context, resource_name):
        # Verify matching tastypie resource exists
        if not resource_name in self.tastypie_api._registry:
            raise Http404
        # Generate mapping from tastypie.resources.Resource.build_schema
        resource = self.tastypie_api._registry.get(resource_name)
        mapping = ResourceSwagger2Mapping(resource)
        basePath, apis, defs, tags = mapping.build_apis()
        if context.get('basePath') is None:
            context['basePath'] = basePath
        context['paths'].update(apis)
        context['definitions'].update(defs)
        context['tags'].extend(tags)
        return context

    def get_context_data(self, *args, **kwargs):
        context = super(SwaggerSpecs2View, self).get_context_data(
            *args, **kwargs)

        # build meta specs
        title = getattr(self.tastypie_api, 'title', self.tastypie_api.api_name)
        descr = getattr(
            self.tastypie_api, 'description', self.tastypie_api.api_name)
        version = getattr(
            self.tastypie_api, 'version', "1.0")
        basePath = getattr(self.tastypie_api, 'basePath', None)
        # create output
        context.update({
            "swagger": "2.0",
            "info": {
                "title": title,
                "description": descr,
                "version": version,
            },
            "host": self.request.get_host(),
            "schemes": [
                "https" if self.request.is_secure() else 'http',
            ],
            "basePath": basePath,
            "produces": [
                "application/json"
            ],
            "tags": [],
            "paths": {
            },
            "definitions": {
            },
        })

        # support meta specifications in Api resource
        api_info = getattr(self.tastypie_api, 'info', False)
        if api_info:
            context['info'].update(api_info)

        # remove invalid attributes
        context.pop('namespace')
        context.pop('version')
        for name in sorted(self.tastypie_api._registry.keys()):
            self.get_resource(context, name)
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
            'models': mapping.build_models(),
            'resourcePath': '/{0}'.format(resource._meta.resource_name)
        })
        return context
