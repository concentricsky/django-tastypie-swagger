from tastypie_swagger.mapping import ResourceSwaggerMapping

SWAGGER_V2_TYPE_MAP = {
    'List': ('array', None),
    'int': ('integer', 'int32'),
    'bool': ('boolean', None),
    'related': ('string', None),
    'datetime': ('string', 'date-time'),
    'decimal': ('number', 'double'),
    'dict': ('object', None),
}


class ResourceSwagger2Mapping(ResourceSwaggerMapping):

    """
    build the 'paths' and 'definitions' entries in a swagger V2 spec

    This uses the original ResourceSwaggerMapping for swagger V1 specs
    and maps its output to Swagger V2. This ensures we can produce both
    valid V1 and V2 specs from the same tastypie.Resources.

    Usage:
        resource = tastypie.Resource instance
        mapping = ResourceSwagger2Mapping(resource)
        common_path, paths, defs, tags = mapping.build_apis()
        specs['paths'].update(apis)
        specs['definitions'].update(defs)

    Parameters:

        resource - the tastypie.Resource instance

    Returns:
        tuple of (common_path, paths, defs, tags)

        common_path - the common parts of the API's URIs, use as "basePath"
        paths - the "path" dict of the specs
        defs - the "definitions" dict of the specs
        tags - the "tags" dict of the specs

    Notes:
        * Any tastypie common dataTypes referenced in the V1 specs are mapped
          as "$ref" and the data type is added to the defs dict. To ensure
          uniqueness among multiple resources, the ListView, Object and Meta
          datatypes are prefixed with the resource name

        * any parameter's "in" attribute for GET methods are set to "query",
          all other methods GET/DELETE/PUT/PATCH get "body".

        * if the parameter name appears as "{<name>}" in the operation's
          path (e.g. parameter "id" in "/category/{id}"), the "in" attribute
          is set to "path" (see map_parameters)

        * types are converted from swagger V1 according to SWAGGER_V2_TYPE_MAP
          (see .get_swagger_type)

        * multi-level model properties are supported, however multi-level
          parameters are not unless they are data types.

    Developers:

        IF YOU UPDATE THIS, BE SURE TO RUN validation tests in

        $ cd example
        $ manage.py test demo
    """

    def build_apis(self):
        apis = [self.build_list_api(), self.build_detail_api()]
        apis.extend(self.build_extra_apis())
        # build the swagger v2 specs
        paths = {}
        defs = {}
        api_tags = []
        api_tagnames = []
        models = self.build_models()
        common_path = apis[0].get('path').replace(self.resource_name, '')
        common_path = common_path.replace('//', '/')
        # build tags, paths and operations
        for api in apis:
            uri = api.get('path').replace(common_path, '/')
            tag_name = uri.replace('/', '').split('{')[0]
            tag = {
                "name": tag_name,
            }
            if tag_name not in api_tagnames:
                api_tagnames.append(tag_name)
                api_tags.append(tag)
            path = paths[uri] = {}
            for op in api.get('operations'):
                responseCls = op.get('responseClass')
                method = op.get('httpMethod').lower()
                path[method] = {
                    "summary": op.get('summary'),
                    # -- note "tags" is optional, yet sphinx-swagger
                    # requires it
                    # (https://github.com/unaguil/sphinx-swagger/issues/5)
                    "tags": [tag_name],
                    "responses": {
                        "200": {
                            "description": "%s object" % responseCls,
                            "schema": {
                                "$ref": self.get_model_ref(responseCls),
                            }
                        }
                    }
                }
                # add optional attributes
                if self.resource.__doc__ is not None:
                    description = self.resource.__doc__
                    path[method].update(description=description)
                # add parameters
                op_params = self.map_parameters(
                    method, uri, op.get('parameters'), models)
                path[method]['parameters'] = op_params
        # build definitions
        for name, model in models.items():
            model.pop('id')
            self.map_properties(model, models)
            # add actual definition object
            defs[self.get_model_ref_name(name)] = model
            # need a 'type' on every level according to JsonSchema specs
            defs[self.get_model_ref_name(name)]['type'] = 'object'
        return common_path, paths, defs, api_tags

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
                param.update(self.get_swagger_type(kind))
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
                    prop.update(self.get_swagger_type(kind))
                ref = prop.get('$ref')
                if ref is not None and not ref.startswith('#'):
                    prop['$ref'] = self.get_model_ref(ref)
                for key, subprop in prop.items():
                    recurse(subprop)
            # if a type is referenced remove 'type' and 'descriptions'
            # to avoid warning 'other properties are defined at level ...'
            # see https://github.com/go-swagger/go-swagger/issues/901
            if '$ref' in prop and 'type' in prop:
                del prop['type']
                del prop['description']
        recurse(props)

    def get_model_ref_name(self, name):
        """
        return unique ref name for definitions

        This is required because the Swagger V1 specs were on a per-resource
        level, whereas the Swagger V2 specs are for multiple resources.
        """
        if name in ['ListView', 'Objects', 'Meta', 'Object']:
            name = '%s_%s' % (self.resource_name.replace('/', '_'),
                              name)
        return name

    def get_model_ref(self, name):
        """
        return the $ref path for the given model name
        """
        return "#/definitions/%s" % self.get_model_ref_name(name)

    def get_swagger_type(self, kind):
        """ return dict of type and format as applicable """
        try:
            kind, format = SWAGGER_V2_TYPE_MAP[kind]
        except KeyError:
            format = None
        d = dict(type=kind)
        if format:
            d.update(format=format)
        return d

    def build_models(self):
        models = super(ResourceSwagger2Mapping, self).build_models()
        # add extra actions models
        # TODO support other models than 'Object', i.e. using response_class
        #      for this use different properties than those returned by
        #      by build_properties_from_field
        if hasattr(self.resource._meta, 'extra_actions'):
            for action in self.resource._meta.extra_actions:
                http_method = action.get('http_method')
                resource_name = '%s_%s' % (self.resource._meta.resource_name,
                                           'Object')
                model_id = '%s_%s' % (self.resource_name, http_method)
                model = self.build_model(
                    resource_name=resource_name,
                    properties=self.build_properties_from_fields(
                        method=http_method),
                    id=model_id,
                )
                models.update(model)
        return models
