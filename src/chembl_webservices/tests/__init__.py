__author__ = 'jfmosquera'

import time
import unittest
import requests
import urllib.parse
from random import randint
# TODO use read timeot to fail tests and prompt the failed URL
from requests.exceptions import ReadTimeout


class BaseWebServiceTestCase(unittest.TestCase):

    # ------------------------------------------------------------------------------------------------------------------
    # Class Variables
    # ------------------------------------------------------------------------------------------------------------------

    resource = None
    id_property = None
    resource_expected_count = -1
    mandatory_properties = []
    sorting_test_props = []

    # ------------------------------------------------------------------------------------------------------------------
    # Testing Constants
    # ------------------------------------------------------------------------------------------------------------------

    TIMEOUT = 30
    API_BASE_URL = 'https://www.ebi.ac.uk/chembl/api'
    WS_URL = API_BASE_URL + '/data'
    WS_URL = 'http://localhost:8000/chembl/api/data'
    UTIL_URL = API_BASE_URL + '/utils'

    TEST_STRUCTURES = False

    # ------------------------------------------------------------------------------------------------------------------
    # TestCase Override
    # ------------------------------------------------------------------------------------------------------------------

    def setUp(self):
        super(BaseWebServiceTestCase, self).setUp()
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        if t > 5:
            print("SLOW TEST RUN: {0} secs :".format(t), end='', flush=True)

    # ------------------------------------------------------------------------------------------------------------------
    # helper functions nested properties
    # ------------------------------------------------------------------------------------------------------------------

    def assert_mandatory_property_nested(self, nested_path, document):
        assert_msg = 'Mandatory property {0} is not present in {1}.'.format(nested_path, self.resource)
        path_parts = nested_path.split('.')
        current_dict = document
        for path_i in path_parts:
            self.assertTrue(isinstance(current_dict, dict) or isinstance(current_dict, list), assert_msg)
            if isinstance(current_dict, dict):
                self.assertIn(path_i, current_dict, assert_msg)
                current_dict = current_dict[path_i]
            elif isinstance(current_dict, list):
                next_level = []
                for list_item_j in current_dict:
                    self.assertIsInstance(list_item_j, dict, assert_msg)
                    self.assertIn(path_i, list_item_j, assert_msg)
                    next_level.append(list_item_j)
            else:
                self.fail(assert_msg)

    # ------------------------------------------------------------------------------------------------------------------
    # helper functions from beaker
    # ------------------------------------------------------------------------------------------------------------------

    def ctab2inchi(self, molfile):
        response = requests.post(self.UTIL_URL+'/ctab2inchi', data=molfile, timeout=self.TIMEOUT)
        return response.text

    # ------------------------------------------------------------------------------------------------------------------
    # helper functions web service access
    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def get_plural(resource_name):
        if resource_name == 'atc_class':
            return 'atc'
        elif resource_name[-1] == 's':
            return resource_name + 'es'
        elif resource_name[-1] == 'y' and resource_name[-2] not in 'aeiou':
            return resource_name[:-1] + 'ies'
        return resource_name + 's'

    def request_url(self, url, expected_code=200, custom_format='json'):
        response = requests.get(url, timeout=self.TIMEOUT)
        self.assertEqual(response.status_code, expected_code, 'The response code does not match for {0}'.format(url))
        if response.status_code == 200:
            if custom_format == 'json':
                return response.json()
            elif custom_format == 'png':
                return response.content
            return response.text
        return None

    def get_resource_by_id(self, resource_name, res_id, custom_format='json', expected_code=200):
        res_id = '{0}'.format(res_id)
        req_url = self.WS_URL + '/{0}/{1}.{2}'.format(resource_name, urllib.parse.quote(res_id), custom_format)
        return self.request_url(req_url, expected_code=expected_code, custom_format=custom_format)

    def get_resource_list(self, resource_name, url_params=None, custom_format='json', expected_code=200):
        params_str = []
        if isinstance(url_params, list) or isinstance(url_params, tuple):
            for tuple_params in url_params:
                params_str.append('{0}={1}'.format(tuple_params[0], urllib.parse.quote('{0}'.format(tuple_params[1]))))
        elif isinstance(url_params, dict):
            for key, value in url_params.items():
                params_str.append('{0}={1}'.format(key, urllib.parse.quote('{0}'.format(value))))
        req_url = self.WS_URL + '/{0}.{1}?{2}'.format(resource_name, custom_format, '&'.join(params_str))
        return self.request_url(req_url, custom_format=custom_format, expected_code=expected_code)

    def get_resource_list_by_ids(self, resource_name, res_ids):
        req_url = self.WS_URL + '/{0}/set/{1}.json'.format(resource_name, urllib.parse.quote(';'.join(res_ids)))
        return self.request_url(req_url)[self.get_plural(resource_name)]

    # ------------------------------------------------------------------------------------------------------------------
    # helper functions for structure searches
    # ------------------------------------------------------------------------------------------------------------------

    def get_similar_molecules(self, smiles, similarity):
        req_url = self.WS_URL + '/similarity/{0}/{1}.json'.format(urllib.parse.quote(smiles), similarity)
        return self.request_url(req_url, expected_code=200)

    def get_substructure_molecules(self, smiles):
        req_url = self.WS_URL + '/substructure/{0}.json'.format(urllib.parse.quote(smiles))
        return self.request_url(req_url, expected_code=200)

    # ------------------------------------------------------------------------------------------------------------------
    # helper functions for resource calls
    # ------------------------------------------------------------------------------------------------------------------

    def get_current_plural(self):
        return BaseWebServiceTestCase.get_plural(self.resource)

    def test_all(self):
        if self.resource:
            resource_req = self.get_resource_list(self.resource)
            total_count = resource_req['page_meta']['total_count']
            self.assertEqual(total_count, self.resource_expected_count)
            first_resources = resource_req[self.get_current_plural()]
            if self.mandatory_properties:
                for res_doc_i in first_resources:
                    for prop_j in self.mandatory_properties:
                        self.assert_mandatory_property_nested(prop_j, res_doc_i)
            if self.sorting_test_props and self.id_property:
                for prop_i in self.sorting_test_props:
                    asc_req = self.get_current_resource_list({'order_by': prop_i})
                    first_asc = asc_req[self.get_current_plural()][0]
                    desc_req = self.get_current_resource_list({'order_by': '-'+prop_i})
                    first_desc = desc_req[self.get_current_plural()][0]
                    self.assertNotEqual(first_asc[self.id_property], first_desc[self.id_property])

            # simple XML and YAML test
            self.get_resource_list(self.resource, url_params={'offset':randint(0, min(total_count, 1000)-20)},
                                   custom_format='xml', expected_code=200)
            self.get_resource_list(self.resource, url_params={'offset':randint(0, min(total_count, 1000)-20)},
                                   custom_format='yaml', expected_code=200)

            # # unknown format test TODO: UNKNOWN formats defaults to XML
            # self.get_resource_list(self.resource, custom_format='pdb', expected_code=404)
            # self.get_resource_list(self.resource, custom_format='sql', expected_code=404)

    def get_current_resource_by_id(self, res_id, custom_format='json', expected_code=200):
        if self.resource:
            return self.get_resource_by_id(self.resource, res_id, custom_format, expected_code)
        self.fail('Test Case does not have a Web Services resource defined.')

    def get_current_resource_list(self, url_params):
        if self.resource:
            return self.get_resource_list(self.resource, url_params)
        self.fail('Test Case does not have a Web Services resource defined.')

    def get_current_resource_list_by_ids(self, res_ids):
        if self.resource:
            return self.get_resource_list_by_ids(self.resource, res_ids)
        self.fail('Test Case does not have a Web Services resource defined.')


if __name__ == '__main__':
    unittest.main()
