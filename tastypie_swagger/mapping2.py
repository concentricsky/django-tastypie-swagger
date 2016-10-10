import logging
from os.path import commonprefix
from tastypie_swagger.mapping import ResourceSwaggerMapping
logger = logging.getLogger(__name__)
# Ignored POST fields
IGNORED_FIELDS = ['id', ]


# Enable all basic ORM filters but do not allow filtering across relationships.
ALL = 1
# Enable all ORM filters, including across relationships
ALL_WITH_RELATIONS = 2

SWAGGER_V2_TYPE_MAP = {
    'List': 'array',
    'int': 'integer',
    'bool': 'boolean',
}


class ResourceSwagger2Mapping(ResourceSwaggerMapping):

    """
    build the 'paths' and 'definitions' entries in a swagger V2 spec

    This uses the original ResourceSwaggerMapping for swagger V1 specs
    and maps its output to Swagger V2. This ensures we can produce both
    valid V1 and V2 specs.

    Usage:
        resource = tastypie.Resource instance
        mapping = ResourceSwagger2Mapping(resource)
        apis, defs = mapping.build_apis()
        specs['paths'].update(apis)
        specs['definitions'].update(defs)
    """

    def build_apis(self):
        apis = [self.build_list_api(), self.build_detail_api()]
        apis.extend(self.build_extra_apis())
        # build the swagger v2 specs
        paths = {}
        defs = {}
        models = self.build_models()
        common_path = apis[0].get('path').replace(self.resource_name, '')
        common_path = common_path.replace('//', '/')
        for api in apis:
            uri = api.get('path').replace(common_path, '/')
            path = paths[uri] = {}
            for op in api.get('operations'):
                responseCls = op.get('responseClass')
                method = op.get('httpMethod').lower()
                path[method] = {
                    "summary": op.get('summary'),
                    "responses": {
                        "200": {
                            "description": "%s object" % responseCls,
                            "schema": {
                                "$ref": self.get_model_ref(responseCls),
                            }
                        }
                    }
                }
                op_params = self.map_parameters(
                    method, uri, op.get('parameters'), models)
                path[method]['parameters'] = op_params
        for name, model in models.iteritems():
            model.pop('id')
            self.map_properties(model, models)
            defs[self.get_model_ref_name(name)] = model
        return common_path, paths, defs

    def map_parameters(self, method, path, in_params, models):
        """
        return "parameters" dictionary
        """
        params = []
        for in_p in in_params:
            # default "in" is query or body
            if method == 'get':
                param_in = 'query'
            else:
                param_in = 'body'
            # check if the parameter name is in path as {name}
            name = in_p.get('name')
            if '{%s}' % name.strip() in path:
                param_in = 'path'
            param = {
                'name': name,
                'in': param_in,
                'required': in_p.get('required'),
            }
            kind = in_p.get('dataType')
            if method != 'get' and kind in models:
                param['schema'] = {
                    "$ref": self.get_model_ref(kind),
                }
            else:
                param['type'] = SWAGGER_V2_TYPE_MAP.get(kind, kind)
            params.append(param)
        return params

    def map_properties(self, model, models):
        """
        recursively map a model's properties to 'definitions' syntax

        This will create entries for 'definitions'. Types in their
        own right are mapped using $ref references. 
        """
        props = model.get('properties')
        def recurse(prop):
            if isinstance(prop, dict):
                kind = prop.get('type')
                if kind in models:
                    prop['type'] = 'object'
                    prop['$ref'] = self.get_model_ref(kind)
                elif kind:
                    prop['type'] = SWAGGER_V2_TYPE_MAP.get(kind, kind)
                ref = prop.get('$ref')
                if ref is not None and not ref.startswith('#'):
                    prop['$ref'] = self.get_model_ref(ref)
                for key, subprop in prop.iteritems():
                    recurse(subprop)
        recurse(props)

    def get_model_ref_name(self, name):
        """
        return unique ref name for definitions

        This is required because the Swagger V1 specs were on a per-resource
        level, whereas the Swagger V2 specs are for multiple resources. 
        """
        if name in ['ListView', 'Objects', 'Meta']:
            name = '%s_%s' % (self.resource_name.replace('/', '_'),
                              name)
        return name

    def get_model_ref(self, name):
        """
        return the $ref path for the given model name
        """
        return "#/definitions/%s" % self.get_model_ref_name(name)
