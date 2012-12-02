from django.core.urlresolvers import reverse

from .utils import trailing_slash_or_none, urljoin_forced


# Ignored POST fields
IGNORED_FIELDS = ['id', ]

# Enable all basic ORM filters but do not allow filtering across relationships.
ALL = 1
# Enable all ORM filters, including across relationships
ALL_WITH_RELATIONS = 2

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

    def build_parameters_from_filters(self, prefix=""):
        parameters = []
        if 'filtering' in self.schema:
            for name, field in self.schema['filtering'].items():
                # Integer value means this points to a related model
                if isinstance( field, int ):
                    if field == ALL: #TODO: Show all possible ORM filters for this field
                        pass
                    elif field == ALL_WITH_RELATIONS: # Show all params from related model
                        related_resource = self.resource.fields[name].get_related_resource(None)
                        related_mapping = ResourceSwaggerMapping(related_resource)
                        parameters.extend(related_mapping.build_parameters_from_filters(prefix="%s%s__" % (prefix, related_mapping.resource_name)))
                elif isinstance( field, list ):
                    # Skip if this is an incorrect filter
                    if name not in self.schema['fields']: continue

                    schema_field = self.schema['fields'][name]
                    for query in field:
                        parameters.append(self.build_parameter(
                            paramType="query",
                            name="%s%s__%s" % (prefix, name, query),
                            dataType=schema_field['type'],
                            required=schema_field['blank'],
                            description=unicode(schema_field['help_text']),
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
            'parameters': self.build_parameters_from_filters(),
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

