import datetime
import logging

from django.db.models.sql.constants import QUERY_TERMS

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_text as force_text


from tastypie import fields

from .utils import trailing_slash_or_none, urljoin_forced

logger = logging.getLogger(__name__)
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
    WRITE_ACTION_IGNORED_FIELDS = ['id', 'resource_uri',]

    # Default summary strings for operations
    OPERATION_SUMMARIES = {
        'get-detail': "Retrieve a single %s by ID",
        'get-list': "Retrieve a list of %s",
        'post-list': "Create a new %s",
        'put-detail': "Update an existing %s",
        'delete-detail': "Delete an existing %s",
    }

    def __init__(self, resource):
        self.resource = resource
        self.resource_name = self.resource._meta.resource_name
        self.resource_pk_type = self.get_pk_type()
        self.schema = self.resource.build_schema()

    def _get_native_field_type(self, field):
        if not field:
            logger.warning('No id field found for resource:{0}'.format(self.resource))
            return 'undefined'
        elif getattr(field, 'is_related', False) and field.is_related:
            if getattr(field, 'is_m2m', False) and field.is_m2m:
                return 'list'
            else:
                related_id_field = field.to_class.base_fields.get('id')
                if related_id_field:
                    return related_id_field.dehydrated_type
        else:
            return field.dehydrated_type

    def get_pk_type(self):
        return self._get_native_field_type(getattr(self.resource, 'id', self.resource.fields.get('id', None)))

    def get_related_field_type(self, related_field_name):
        for field_name, field in self.resource.base_fields.items():
            if related_field_name == field_name:
                return self._get_native_field_type(field)

    def get_resource_verbose_name(self, plural=False):
        """Retrieve the verbose name for the resource from the queryset model.

        If the resource is not a ModelResource, use either
        ``resource_name`` or ``resource_name_plural``.
        """
        qs = self.resource._meta.queryset
        if qs is not None and hasattr(qs, 'model'):
            meta = qs.model._meta
            verbose_name = meta.verbose_name_plural if plural else meta.verbose_name
            return verbose_name.lower()

        if plural and getattr(self.resource._meta, 'resource_name_plural', ""):
            return self.resource._meta.resource_name_plural
        return self.resource_name

    def get_operation_summary(self, detail=True, method='get'):
        """
        Get a basic summary string for a single operation
        """
        key = '%s-%s' % (method.lower(), detail and 'detail' or 'list')
        plural = not detail and method is 'get'
        verbose_name = self.get_resource_verbose_name(plural=plural)
        summary = self.OPERATION_SUMMARIES.get(key, '')
        if summary:
            return summary % verbose_name
        return ''

    def get_resource_base_uri(self):
        """
        Use Resource.get_resource_list_uri (or Resource.get_resource_uri, depending on version of tastypie)
        to get the URL of the list endpoint

        We also use this to build the detail url, which may not be correct
        """
        if hasattr(self.resource, 'get_resource_list_uri'):
            return self.resource.get_resource_list_uri()
        elif hasattr(self.resource, 'get_resource_uri'):
            return self.resource.get_resource_uri()
        else:
            raise AttributeError('Resource %(resource)s has neither get_resource_list_uri nor get_resource_uri' % {'resource': self.resource})

    def build_parameter(self, paramType='body', name='', dataType='', required=True, description='', allowed_values = None):
        parameter = {
            'paramType': paramType,
            'name': name,
            'dataType': dataType if dataType is not None else 'unknown',
            'required': required,
            'description': description,
        }

        # TODO make use of this to Implement the allowable_values of swagger
        # (https://github.com/wordnik/swagger-core/wiki/Datatypes) at the field level.
        # This could be added to the meta value of the resource to specify enum-like or range data on a field.
#        if allowed_values:
#            parameter.update({'allowableValues': allowed_values})
        return parameter

    def build_parameters_from_fields(self):
        parameters = []
        for name, field in self.schema['fields'].items():
            # Ignore readonly fields
            if not field['readonly'] and not name in IGNORED_FIELDS:
                parameters.append(self.build_parameter(
                    name=name,
                    dataType=field['type'],
                    required=not field['blank'],
                    description=force_text(field['help_text']),
                ))
        return parameters

    def build_parameters_for_list(self, method='GET'):
        parameters = self.build_parameters_from_filters(method=method)

        # So far use case for ordering are only on GET request.
        if 'ordering' in self.schema and method.upper() == 'GET':
            parameters.append(self.build_parameters_from_ordering())
        return parameters

    def build_parameters_from_ordering(self):
        values = []
        [values.extend([field,"-%s"%field]) for field in self.schema['ordering']]
        return {
            'paramType': "query",
            'name': "order_by",
            'dataType': "String",
            'required': False,
            'description': unicode("Orders the result set based on the selection. "
                                   "Ascending order by default, prepending the '-' "
                                   "sign change the sorting order to descending"),
            'allowableValues': {
                'valueType' : "LIST",
                'values': values

            }
        }

    def build_parameters_from_filters(self, prefix="", method='GET'):
        parameters = []

        # Deal with the navigational filters.
        # Always add the limits & offset params on the root ( aka not prefixed ) object.
        if not prefix and method.upper() == 'GET':
            navigation_filters = [
                ('limit', 'int', 'Specify the number of element to display per page.'),
                ('offset', 'int', 'Specify the offset to start displaying element on a page.'),
            ]
            for name, type, desc in navigation_filters:
                parameters.append(self.build_parameter(
                    paramType="query",
                    name=name,
                    dataType=type,
                    required=False,
                    description=force_text(desc),
                ))
        if 'filtering' in self.schema and method.upper() == 'GET':
            for name, field in self.schema['filtering'].items():
                # Avoid infinite recursion for self referencing resource (issue #22)
                if not prefix.find('{0}__'.format(name)) >= 0:
                    # Integer value means this points to a related model
                    if field in [ALL, ALL_WITH_RELATIONS]:
                        # For fields marked as ALL_WITH_RELATIONS, we must fetch information on their related resources as well.
                        # However, tastypie allows us to mark fields that do not have related resources as ALL_WITH_RELATIONS.
                        # This functions like a white list.
                        # Therefore, we need to check whether a field actually has a related resource.
                        if field == ALL:
                            has_related_resource = False
                        else:
                            has_related_resource = hasattr(self.resource.fields[name], 'get_related_resource')

                        if not has_related_resource:
                            #This code has been mostly sucked from the tastypie lib
                            if getattr(self.resource._meta, 'queryset', None) is not None:
                                # Get the possible query terms from the current QuerySet.
                                if hasattr(self.resource._meta.queryset.query.query_terms, 'keys'):
                                    # Django 1.4 & below compatibility.
                                    field = self.resource._meta.queryset.query.query_terms.keys()
                                else:
                                    # Django 1.5+.
                                    field = self.resource._meta.queryset.query.query_terms
                            else:
                                if hasattr(QUERY_TERMS, 'keys'):
                                    # Django 1.4 & below compatibility.
                                    field = QUERY_TERMS.keys()
                                else:
                                    # Django 1.5+.
                                    field = QUERY_TERMS

                        else: # Show all params from related model
                            # Add a subset of filter only foreign-key compatible on the relation itself.
                            # We assume foreign keys are only int based.
                            field = ['gt', 'in', 'gte', 'lt', 'lte', 'exact'] # TODO This could be extended by checking the actual type of the relational field, but afaik it's also an issue on tastypie.
                            related_resource = self.resource.fields[name].get_related_resource(None)
                            related_mapping = ResourceSwaggerMapping(related_resource)

                            parameters.extend(related_mapping.build_parameters_from_filters(prefix="%s%s__" % (prefix, name)))

                    if isinstance(field, (list, tuple, set)):
                        # Skip if this is an incorrect filter
                        if name not in self.schema['fields']: continue

                        schema_field = self.schema['fields'][name]

                        dataType = schema_field['type']
                        if dataType == 'related':
                            dataType = self.get_related_field_type(name)
                            description = 'ID of related resource'

                        for query in field:
                            if query == 'exact':
                                description = force_text(schema_field['help_text'])

                                # Use a better description for related models with exact filter
                                parameters.append(self.build_parameter(
                                    paramType="query",
                                    name="%s%s" % (prefix, name),
                                    dataType=dataType,
                                    required = False,
                                    description=description,
                                ))
                            else:
                                parameters.append(self.build_parameter(
                                    paramType="query",
                                    name="%s%s__%s" % (prefix, name, query),
                                    dataType=dataType,
                                    required = False,
                                    description=force_text(schema_field['help_text']),
                                ))

        return parameters

    def build_parameter_for_object(self, method='get'):
        return self.build_parameter(
            name=self.resource_name,
            dataType="%s_%s" % (self.resource_name, method) if not method == "get" else self.resource_name,
            required = True
        )

    def _detail_uri_name(self):
        # For compatibility with TastyPie 0.9.11, which doesn't define a
        # detail_uri_name by default.
        detail_uri_name = getattr(self.resource._meta, "detail_uri_name", "pk")
        return detail_uri_name == "pk" and "id" or detail_uri_name

    def build_parameters_from_extra_action(self, method, fields, resource_type):
        parameters = []
        if resource_type == "view":
            parameters.append(self.build_parameter(paramType='path',
                              name=self._detail_uri_name(),
                              dataType=self.resource_pk_type,
                              description='Primary key of resource'))
        for name, field in fields.items():
            parameters.append(self.build_parameter(
                paramType=field.get("param_type", "query"),
                name=name,
                dataType=field.get("type", "string"),
                required=field.get("required", True),
                description=force_text(field.get("description", "")),
            ))

        # For non-standard API functionality, allow the User to declaritively
        # define their own filters, along with Swagger endpoint values.
        # Minimal error checking here. If the User understands enough to want to
        # do this, assume that they know what they're doing.
        if hasattr(self.resource.Meta, 'custom_filtering'):
            for name, field in self.resource.Meta.custom_filtering.items():
                parameters.append(self.build_parameter(
                                  paramType='query',
                                  name=name,
                                  dataType=field['dataType'],
                                  required=field['required'],
                                  description=unicode(field['description'])
                                  ))


        return parameters

    def build_detail_operation(self, method='get'):
        operation = {
            'summary': self.get_operation_summary(detail=True, method=method),
            'httpMethod': method.upper(),
            'parameters': [
                self.build_parameter(
                    paramType='path',
                    name=self._detail_uri_name(),
                    dataType=self.resource_pk_type,
                    description='Primary key of resource'
                ),
            ],
            'responseClass': self.resource_name,
            'nickname': '%s_detail' % self.resource_name,
            'notes': self.resource.__doc__,
        }
        return operation

    def build_list_operation(self, method='get'):
        return {
            'summary': self.get_operation_summary(detail=False, method=method),
            'httpMethod': method.upper(),
            'parameters': self.build_parameters_for_list(method=method),
            'responseClass': 'ListView' if method.upper() == 'GET' else self.resource_name,
            'nickname': '%s_list' % self.resource_name,
            'notes': self.resource.__doc__,
        }

    def build_extra_operation(self, extra_action):
        if "name" not in extra_action:
            raise LookupError("\"name\" is a required field in extra_actions.")
        return {
            'summary': extra_action.get("summary", ""),
            'httpMethod': extra_action.get('http_method', "get").upper(),
            'parameters': self.build_parameters_from_extra_action(
                method=extra_action.get('http_method'),
                # Default fields to an empty dictionary in the case that it
                # is not set.
                fields=extra_action.get('fields', {}),
                resource_type=extra_action.get("resource_type", "view")),
            'responseClass': 'Object', #TODO this should be extended to allow the creation of a custom object.
            'nickname': extra_action['name'],
            'notes': extra_action.get('notes', ''),
        }

    def build_detail_api(self):
        detail_api = {
            'path': urljoin_forced(self.get_resource_base_uri(), '{%s}%s' % (self._detail_uri_name(), trailing_slash_or_none())),
            'operations': [],
        }

        if 'get' in self.schema['allowed_detail_http_methods']:
            detail_api['operations'].append(self.build_detail_operation(method='get'))

        if 'put' in self.schema['allowed_detail_http_methods']:
            operation = self.build_detail_operation(method='put')
            operation['parameters'].append(self.build_parameter_for_object(method='put'))
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
            operation['parameters'].append(self.build_parameter_for_object(method='post'))
            list_api['operations'].append(operation)

        return list_api

    def build_extra_apis(self):
        extra_apis = []
        if hasattr(self.resource._meta, 'extra_actions'):
            identifier = self._detail_uri_name()
            for extra_action in self.resource._meta.extra_actions:
                extra_api = {
                    'path': "%s{%s}/%s/" % (self.get_resource_base_uri(), identifier , extra_action.get('name')),
                    'operations': []
                }

                if extra_action.get("resource_type", "view") == "list":
                    extra_api['path'] = "%s%s/" % (self.get_resource_base_uri(), extra_action.get('name'))

                operation = self.build_extra_operation(extra_action)
                extra_api['operations'].append(operation)
                extra_apis.append(extra_api)
        return extra_apis

    def build_apis(self):
        apis = [self.build_list_api(), self.build_detail_api()]
        apis.extend(self.build_extra_apis())
        return apis

    def build_property(self, name, type, description=""):
        prop = {
            name: {
                'type': type,
                'description': description,
            }
        }

        if type == 'List':
            prop[name]['items'] = {'$ref': name}

        return prop

    def build_properties_from_fields(self, method='get'):
        properties = {}
        excludes = getattr(self.resource._meta, 'excludes', [])
        for name, field in self.schema['fields'].items():
            if name in excludes:
                continue
            # Exclude fields from custom put / post object definition
            if method in ['post','put']:
                if name in self.WRITE_ACTION_IGNORED_FIELDS:
                    continue
                if field.get('readonly'):
                    continue
            # Deal with default format
            if isinstance(field.get('default'), fields.NOT_PROVIDED):
                field['default'] = None
            elif isinstance(field.get('default'), datetime.datetime):
                field['default'] = field.get('default').isoformat()

            properties.update(self.build_property(
                    name,
                    field.get('type'),
                    # note: 'help_text' is a Django proxy which must be wrapped
                    # in unicode *specifically* to get the actual help text.
                    force_text(field.get('help_text', '')),
                )
            )
        return properties

    def build_model(self, resource_name, id, properties):
        return {
            resource_name: {
                'properties': properties,
                'id': id
            }
        }


    def build_list_models_and_properties(self):
        models = {}

        # Build properties added by list view in the meta section by tastypie
        meta_properties = {}
        meta_properties.update(
            self.build_property('limit', 'int', 'Specify the number of element to display per page.')
        )
        meta_properties.update(
            self.build_property('next', 'string', 'Uri of the next page relative to the current page settings.')
        )
        meta_properties.update(
            self.build_property('offset', 'int', 'Specify the offset to start displaying element on a page.')
        )
        meta_properties.update(
            self.build_property('previous', 'string', 'Uri of the previous page relative to the current page settings.')
        )
        meta_properties.update(
            self.build_property('total_count', 'int', 'Total items count for the all collection')
        )

        models.update(
            self.build_model(
                'Meta',
                'Meta',
                meta_properties
            )
        )

        objects_properties = {}
        objects_properties.update(
            self.build_property(
                self.resource_name,
                "List")
        )
        # Build the Objects class added by tastypie in the list view.
        models.update(
            self.build_model(
                'Objects',
                'Objects',
                objects_properties
            )
        )
        # Build the actual List class
        list_properties = {}
        list_properties.update(self.build_property(
            'meta',
            'Meta'
        ))

        list_properties.update(self.build_property(
            'objects',
            'Objects'
        ))
        models.update(
            self.build_model(
                'ListView',
                'ListView',
                list_properties
            )
        )

        return models

    def build_models(self):
        #TODO this should be extended to allow the creation of a custom objects for extra_actions.
        models = {}

        # Take care of the list particular schema with meta and so on.
        if 'get' in self.schema['allowed_list_http_methods']:
            models.update(self.build_list_models_and_properties())

        if 'post' in self.resource._meta.list_allowed_methods:
            models.update(
                self.build_model(
                    resource_name='%s_post' % self.resource._meta.resource_name,
                    properties=self.build_properties_from_fields(method='post'),
                    id='%s_post' % self.resource_name
                )
            )

        if 'put' in self.resource._meta.detail_allowed_methods:
            models.update(
                self.build_model(
                    resource_name='%s_put' % self.resource._meta.resource_name,
                    properties=self.build_properties_from_fields(method='put'),
                    id='%s_put' % self.resource_name
                )
            )

        # Actually add the related model
        models.update(
            self.build_model(
                resource_name=self.resource._meta.resource_name,
                properties=self.build_properties_from_fields(),
                id=self.resource_name
            )
        )
        return models
