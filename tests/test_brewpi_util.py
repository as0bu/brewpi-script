import simplejson
import unittest

import brewpi_util as util


class BrewPiUtilsTestCase(unittest.TestCase):
    # test that characters from extended ascii
    # are removed (except degree symbol)
    def test_ascii_to_unicode_extended_ascii_is_discarded(self):
        s = 'test\xff'
        s = util.ascii_to_unicode(s)
        self.assertEqual(s, u'test')

    # test that degree symbol is replaced by &deg
    def test_ascii_to_unicode_degree_sign(self):
        s = 'temp: 18\xB0C'
        s = util.ascii_to_unicode(s)
        self.assertEqual(s, u'temp: 18&degC')

    def test_ascii_to_unicode_can_be_json_serialized(self):
        s = '{"test": "18\xB0C"}'
        # without next line, error will be:
        # UnicodeDecodeError: 'utf8' codec can't decode byte 0xb0 in
        # position 2: invalid start byte
        s = util.ascii_to_unicode(s)
        simplejson.loads(s)
