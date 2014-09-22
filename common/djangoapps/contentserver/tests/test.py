"""
Tests for StaticContentServer
"""
import copy
import logging
import unittest
from uuid import uuid4

from django.conf import settings
from django.test.client import Client
from django.test.utils import override_settings

from xmodule.contentstore.django import contentstore
from xmodule.modulestore.django import modulestore
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.xml_importer import import_from_xml

from contentserver.middleware import parse_range_header
from student.models import CourseEnrollment

log = logging.getLogger(__name__)

TEST_DATA_CONTENTSTORE = copy.deepcopy(settings.CONTENTSTORE)
TEST_DATA_CONTENTSTORE['DOC_STORE_CONFIG']['db'] = 'test_xcontent_%s' % uuid4().hex


@override_settings(CONTENTSTORE=TEST_DATA_CONTENTSTORE)
class ContentStoreToyCourseTest(ModuleStoreTestCase):
    """
    Tests that use the toy course.
    """

    def setUp(self):
        """
        Create user and login.
        """
        self.staff_pwd = super(ContentStoreToyCourseTest, self).setUp()
        self.staff_usr = self.user
        self.non_staff_usr, self.non_staff_pwd = self.create_non_staff_user()

        self.client = Client()
        self.contentstore = contentstore()

        self.course_key = SlashSeparatedCourseKey('edX', 'toy', '2012_Fall')

        import_from_xml(
            modulestore(), self.user.id, 'common/test/data/', ['toy'],
            static_content_store=self.contentstore, verbose=True
        )

        # A locked asset
        self.locked_asset = self.course_key.make_asset_key('asset', 'sample_static.txt')
        self.url_locked = self.locked_asset.to_deprecated_string()
        self.contentstore.set_attr(self.locked_asset, 'locked', True)

        # An unlocked asset
        self.unlocked_asset = self.course_key.make_asset_key('asset', 'another_static.txt')
        self.url_unlocked = self.unlocked_asset.to_deprecated_string()
        self.length_unlocked = self.contentstore.get_attr(self.unlocked_asset, 'length')

    def test_unlocked_asset(self):
        """
        Test that unlocked assets are being served.
        """
        self.client.logout()
        resp = self.client.get(self.url_unlocked)
        self.assertEqual(resp.status_code, 200)  # pylint: disable=E1103

    def test_locked_asset_not_logged_in(self):
        """
        Test that locked assets behave appropriately in case the user is not
        logged in.
        """
        self.client.logout()
        resp = self.client.get(self.url_locked)
        self.assertEqual(resp.status_code, 403)  # pylint: disable=E1103

    def test_locked_asset_not_registered(self):
        """
        Test that locked assets behave appropriately in case user is logged in
        in but not registered for the course.
        """
        self.client.login(username=self.non_staff_usr, password=self.non_staff_pwd)
        resp = self.client.get(self.url_locked)
        self.assertEqual(resp.status_code, 403)  # pylint: disable=E1103

    def test_locked_asset_registered(self):
        """
        Test that locked assets behave appropriately in case user is logged in
        and registered for the course.
        """
        CourseEnrollment.enroll(self.non_staff_usr, self.course_key)
        self.assertTrue(CourseEnrollment.is_enrolled(self.non_staff_usr, self.course_key))

        self.client.login(username=self.non_staff_usr, password=self.non_staff_pwd)
        resp = self.client.get(self.url_locked)
        self.assertEqual(resp.status_code, 200)  # pylint: disable=E1103

    def test_locked_asset_staff(self):
        """
        Test that locked assets behave appropriately in case user is staff.
        """
        self.client.login(username=self.staff_usr, password=self.staff_pwd)
        resp = self.client.get(self.url_locked)
        self.assertEqual(resp.status_code, 200)  # pylint: disable=E1103

    def test_range_request_full_file(self):
        """
        Test that a range request from byte 0 to last,
        outputs partial content status code and valid Content-Range and Content-Length.
        """
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes=0-')

        self.assertEqual(resp.status_code, 206)  # HTTP_206_PARTIAL_CONTENT
        self.assertEqual(
            resp['Content-Range'],
            'bytes {first}-{last}/{length}'.format(
                first=0, last=self.length_unlocked - 1,
                length=self.length_unlocked
            )
        )
        self.assertEqual(resp['Content-Length'], str(self.length_unlocked))

    def test_range_request_partial_file(self):
        """
        Test that a range request for a partial file,
        outputs partial content status code and valid Content-Range and Content-Length.
        first_byte and last_byte are chosen to be simple but non trivial values.
        """
        first_byte = self.length_unlocked / 4
        last_byte = self.length_unlocked / 2
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes={first}-{last}'.format(
            first=first_byte, last=last_byte)
        )

        self.assertEqual(resp.status_code, 206)  # HTTP_206_PARTIAL_CONTENT
        self.assertEqual(resp['Content-Range'], 'bytes {first}-{last}/{length}'.format(
            first=first_byte, last=last_byte, length=self.length_unlocked))
        self.assertEqual(resp['Content-Length'], str(last_byte - first_byte + 1))

    def test_range_request_multiple_ranges(self):
        """
        Test that multiple ranges in request outputs the full content.
        """
        first_byte = self.length_unlocked / 4
        last_byte = self.length_unlocked / 2
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes={first}-{last}, -100'.format(
            first=first_byte, last=last_byte)
        )

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('Content-Range', resp)
        self.assertEqual(resp['Content-Length'], str(self.length_unlocked))

    def test_range_request_malformed_missing_equal(self):
        """
        Test that a range request with malformed Range (missing '=') outputs a 200 OK full content response.
        """
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes 0-')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('Content-Range', resp)

    def test_range_request_malformed_not_bytes(self):
        """
        Test that a range request with malformed Range (not "bytes") outputs a 200 OK full content response.
        "Accept-Ranges: bytes" tells the user that only "bytes" ranges are allowed
        """
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bits=0-')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('Content-Range', resp)

    def test_range_request_malformed_missing_minus(self):
        """
        Test that a range request with malformed Range (missing '-') outputs a 200 OK full content response.
        """
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes=0')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('Content-Range', resp)

    def test_range_request_malformed_first_not_integer(self):
        """
        Test that a range request with malformed Range (first is not an integer) outputs a 200 OK full content response.
        """
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes=one-')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('Content-Range', resp)

    def test_range_request_malformed_invalid_range(self):
        """
        Test that a range request with malformed Range (first_byte > last_byte) outputs
        416 Requested Range Not Satisfiable.
        """
        first_byte = self.length_unlocked / 2
        last_byte = self.length_unlocked / 4
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes={first}-{last}'.format(
            first=first_byte, last=last_byte)
        )

        self.assertEqual(resp.status_code, 416)

    def test_range_request_malformed_out_of_bounds(self):
        """
        Test that a range request with malformed Range (first_byte, last_byte == totalLength, offset by 1 error)
        outputs 416 Requested Range Not Satisfiable.
        """
        last_byte = self.length_unlocked
        resp = self.client.get(self.url_unlocked, HTTP_RANGE='bytes={first}-{last}'.format(
            first=last_byte, last=last_byte)
        )

        self.assertEqual(resp.status_code, 416)


class ParseRangeHeaderTestCase(unittest.TestCase):
    """
    Tests for the parse_range_header function.
    """

    def setUp(self):
        self.content_length = 10000

    def test_bytes_unit(self):
        unit, __ = parse_range_header('bytes=100-', self.content_length)
        self.assertEqual(unit, 'bytes')

    def test_invalid_syntax(self):
        self.assertRaisesRegexp(ValueError, 'Invalid syntax', parse_range_header, 'bytes', self.content_length)
        self.assertRaisesRegexp(ValueError, 'Invalid syntax', parse_range_header, 'bytes=', self.content_length)
        self.assertRaisesRegexp(
            ValueError, 'too many values to unpack', parse_range_header, 'bytes=0=', self.content_length
        )
        self.assertRaisesRegexp(ValueError, 'Invalid syntax', parse_range_header, 'bytes=0', self.content_length)
        self.assertRaisesRegexp(ValueError, 'Invalid syntax', parse_range_header, 'bytes=0-10,0', self.content_length)

    def test_byte_range_spec(self):
        __, ranges = parse_range_header('bytes=100-', self.content_length)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0], (100, 9999))

        __, ranges = parse_range_header('bytes=1000-', self.content_length)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0], (1000, 9999))

        __, ranges = parse_range_header('bytes=100-199, 200-', self.content_length)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges, [(100, 199), (200, 9999)])

        __, ranges = parse_range_header('bytes=100-199, 200-499', self.content_length)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges, [(100, 199), (200, 499)])

        self.assertRaisesRegexp(
            ValueError, 'invalid literal for int()', parse_range_header, 'bytes=one-20', self.content_length
        )

    def test_suffix_byte_range_spec(self):
        __, ranges = parse_range_header('bytes=-100', self.content_length)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0], (9900, 9999))

        __, ranges = parse_range_header('bytes=-100, -200', self.content_length)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges, [(9900, 9999), (9800, 9999)])

        self.assertRaisesRegexp(
            ValueError, 'invalid literal for int()', parse_range_header, 'bytes=-one', self.content_length
        )
