import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import vz_delete_tool as vz  # noqa: E402


class ParseServerTest(unittest.TestCase):
    def test_valid(self):
        cases = {
            "192.168.1.100": "http://192.168.1.100",
            "192.168.1.100/": "http://192.168.1.100",
            "raspberrypi": "http://raspberrypi",
            "localhost:8080": "http://localhost:8080",
            "vz.example.com:8080": "http://vz.example.com:8080",
            "https://vz.example.com/middleware.php": "https://vz.example.com/middleware.php",
            "HTTP://10.0.0.1:80/vz/middleware/": "http://10.0.0.1:80/vz/middleware",
            "my-server.home.arpa": "http://my-server.home.arpa",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(vz.parse_server(value), expected)

    def test_invalid(self):
        for value in ["", "999.999.999.999", "256.1.1.1", "192.168.1", "1.2.3.4.5",
                      "ftp://host", "host:0", "host:70000", "-host", "host name", "host:abc"]:
            with self.subTest(value=value):
                self.assertIsNone(vz.parse_server(value))


class TimestampTest(unittest.TestCase):
    def test_unix_ms(self):
        self.assertEqual(vz.convert_to_timestamp("1714566600000"), 1714566600000)

    def test_local_time(self):
        expected = int(datetime(2025, 5, 1, 14, 30).timestamp() * 1000)
        self.assertEqual(vz.convert_to_timestamp("01.05.2025 14:30"), expected)

    def test_invalid(self):
        self.assertIsNone(vz.convert_to_timestamp("2025-05-01"))
        self.assertIsNone(vz.convert_to_timestamp(""))


class ThresholdTest(unittest.TestCase):
    def test_positive(self):
        self.assertTrue(vz.exceeds_threshold(30001, 30000, False))
        self.assertFalse(vz.exceeds_threshold(30000, 30000, False))

    def test_negative(self):
        self.assertTrue(vz.exceeds_threshold(-6000, -4000, True))
        self.assertFalse(vz.exceeds_threshold(-3990, -4000, True))

    def test_value_format(self):
        self.assertTrue(vz.is_valid_decimal_or_integer("123.45"))
        self.assertTrue(vz.is_valid_decimal_or_integer("30000"))
        self.assertFalse(vz.is_valid_decimal_or_integer("12.5"))


class MiscTest(unittest.TestCase):
    def test_uuid(self):
        self.assertTrue(vz.is_valid_uuid("12345678-1234-1234-1234-123456789abc"))
        self.assertFalse(vz.is_valid_uuid("12345678-1234-1234-1234-123456789ab"))

    def test_middleware_error(self):
        self.assertEqual(vz.middleware_error({"exception": {"message": "denied"}}), "denied")
        self.assertIsNone(vz.middleware_error({"data": {}}))


if __name__ == "__main__":
    unittest.main()
