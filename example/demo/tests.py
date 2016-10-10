from django.test.testcases import TestCase
from swagger_spec_validator.util import get_validator
from tastypie.test import ResourceTestCaseMixin


class TestSpecs(ResourceTestCaseMixin, TestCase):

    def setUp(self):
        super(TestSpecs, self).setUp()

    def tearDown(self):
        super(TestSpecs, self).tearDown()

    def test_validate_specs(self):
        for uri in ['/api/doc/specs/swagger.json',
                    '/api/doc/specs/']:
            resp = self.client.get(uri,
                                   format='json')
            self.assertHttpOK(resp)
            spec_json = self.deserialize(resp)
            validator = get_validator(spec_json)
            validator.validate_spec(spec_json)
