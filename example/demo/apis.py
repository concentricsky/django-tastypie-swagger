from demo.models import FooModel, BarModel
from tastypie.api import Api
from tastypie.resources import ModelResource


class FooResource(ModelResource):
    class Meta:
        queryset = FooModel.objects.all()


class BarResource(ModelResource):
    class Meta:
        queryset = BarModel.objects.all()


api = Api('v1')
api.title = 'demo API'
api.description = 'lorem ipsum'
api.version = '1.9'
api.info = {
    'license': {
        'name': 'Apache',
        'url': 'http://www.apache.org/licenses/LICENSE-2.0',
    }}
api.register(FooResource())
api.register(BarResource())
