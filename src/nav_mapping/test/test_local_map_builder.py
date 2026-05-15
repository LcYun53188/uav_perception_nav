import unittest
from nav_mapping.local_map_builder import LocalMapBuilder
from geometry_msgs.msg import TransformStamped

class TestLocalMapBuilder(unittest.TestCase):
    def test_apply_transform(self):
        # Create a dummy transform: translate by (1, 2, 3), no rotation
        t = TransformStamped()
        t.transform.translation.x = 1.0
        t.transform.translation.y = 2.0
        t.transform.translation.z = 3.0
        t.transform.rotation.w = 1.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0

        # Point (0, 0, 0) should become (1, 2, 3)
        res = LocalMapBuilder._apply_transform(0.0, 0.0, 0.0, t)
        self.assertEqual(res, (1.0, 2.0, 3.0))

        # Point (1, 1, 1) should become (2, 3, 4)
        res = LocalMapBuilder._apply_transform(1.0, 1.0, 1.0, t)
        self.assertEqual(res, (2.0, 3.0, 4.0))

    def test_apply_transform_rotation(self):
        # 90 degree rotation around Z axis
        # q = [0, 0, sin(45), cos(45)] = [0, 0, 0.7071, 0.7071]
        t = TransformStamped()
        t.transform.translation.x = 0.0
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.w = 0.70710678118
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.70710678118

        # Point (1, 0, 0) rotated 90 deg around Z should be (0, 1, 0)
        tx, ty, tz = LocalMapBuilder._apply_transform(1.0, 0.0, 0.0, t)
        self.assertAlmostEqual(tx, 0.0, places=5)
        self.assertAlmostEqual(ty, 1.0, places=5)
        self.assertAlmostEqual(tz, 0.0, places=5)

if __name__ == '__main__':
    unittest.main()
