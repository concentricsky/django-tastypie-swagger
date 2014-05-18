from django.test import TestCase
from django.conf import settings

class SchemaTest(TestCase):
    def test_list_endpoint(self):
        self.assertEqual(1,1)
        import ipdb; ipdb.set_trace()
        self.assertEqual(settings.DEBUG, True)
        self.client.get('/')