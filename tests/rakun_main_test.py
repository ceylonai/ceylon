import unittest

import rakun


class MyTestCase(unittest.TestCase):
    def test_something(self):
        res = rakun.rakun.Agent("test")
        assert res.get_name() == "test"


if __name__ == '__main__':
    unittest.main()
