import unittest

import rakun


class MyTestCase(unittest.TestCase):
    def test_something(self):
        res = rakun.rakun.sum_as_string(1, 2)
        self.assertEqual(res, "3")


if __name__ == '__main__':
    unittest.main()
