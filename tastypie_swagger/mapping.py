from django.core.urlresolvers import reverse

from .utils import trailing_slash_or_none, urljoin_forced


# Ignored POST fields
IGNORED_FIELDS = ['id', ]


class ResourceSwaggerMapping(object):
    """
    Represents a mapping of a tastypie resource to a swagger API declaration

    Tries to use tastypie.resources.Resource.build_schema

    http://django-tastypie.readthedocs.org/en/latest/resources.html
    https://github.com/wordnik/swagger-core/wiki/API-Declaration
    """

    def __init__(self, resource):
        self.resource = resource
        self.resource_name = self.resource._meta.resource_name
        self.schema = self.resource.build_schema()

    def get_resource_base_uri(self):
        """
        Use Resource.get_resource_list_uri to get the URL of the list endpoint

        We also use this to build the detail url, which may not be correct
        """
        return self.resource.get_resource_list_uri()

    def build_parameter(self, paramType='body', name='', dataType='', required=True, description=''):
        return {
            'paramType': paramType,
            'name': name,
            'dataType': dataType,
            'required': required,
            'description': description,
        }

    def build_parameters_from_fields(self):   
        parameters = []
        for name, field in self.schema['fields'].items():
            # Ignore readonly fields
            if not field['readonly'] and not name in IGNORED_FIELDS:
                parameters.append(self.build_parameter(
                    name=name,
                    dataType=field['type'],
                    required=not field['blank'],
                    description=unicode(field['help_text']),
                ))
        return parameters

    def build_detail_operation(self, method='get'):
        operation = {
            'httpMethod': method.upper(),
            'parameters': [self.build_parameter(paramType='path', name='id', dataType='int', description='ID of resource')],
            'responseClass': 'Object',
            'nickname': '%s-detail' % self.resource_name,
        }
        return operation

    def build_list_operation(self, method='get'):
        return {
            'httpMethod': method.upper(),
            'parameters': [],
            'responseClass': 'List',
            'nickname': '%s-list' % self.resource_name,
        }

    def build_detail_api(self):
        detail_api = {
            'path': urljoin_forced(self.get_resource_base_uri(), '{id}%s' % trailing_slash_or_none()),
            'operations': [],
        }

        if 'get' in self.schema['allowed_detail_http_methods']:
            detail_api['operations'].append(self.build_detail_operation(method='get'))

        if 'put' in self.schema['allowed_detail_http_methods']:
            operation = self.build_detail_operation(method='put')
            operation['parameters'].extend(self.build_parameters_from_fields())
            detail_api['operations'].append(operation)

        if 'delete' in self.schema['allowed_detail_http_methods']:
            detail_api['operations'].append(self.build_detail_operation(method='delete'))

        return detail_api

    def build_list_api(self):
        list_api = {
            'path': self.get_resource_base_uri(),
            'operations': [],
        }

        if 'get' in self.schema['allowed_list_http_methods']:
            list_api['operations'].append(self.build_list_operation(method='get'))

        if 'post' in self.schema['allowed_list_http_methods']:
            operation = self.build_list_operation(method='post')
            operation['parameters'].extend(self.build_parameters_from_fields())
            list_api['operations'].append(operation)

        return list_api

    def build_apis(self):
        return [self.build_list_api(), self.build_detail_api()]

