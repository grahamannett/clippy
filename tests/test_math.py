import unittest

import numpy as np

from common.math_utils import cosine_similarity, normalize, row_norms


class TestMath(unittest.TestCase):
    def test_normalize(self):
        from sklearn.metrics import pairwise

        x = np.random.rand(1, 10)
        xx = np.random.rand(10, 10)

        self.assertTrue(np.allclose(row_norms(x), pairwise.row_norms(x)))
        self.assertTrue(np.allclose(row_norms(xx), pairwise.row_norms(xx)))

        self.assertTrue(np.allclose(normalize(x), pairwise.normalize(x)))
        self.assertTrue(np.allclose(normalize(xx), pairwise.normalize(xx)))

    def test_cos(self):
        from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

        x = np.random.rand(1, 10)
        xx = np.random.rand(10, 10)
        yy = np.random.rand(100, 10)

        self.assertTrue(np.allclose(cosine_similarity(x, xx), sklearn_cosine_similarity(x, xx)))
        self.assertTrue(np.allclose(cosine_similarity(xx, yy), sklearn_cosine_similarity(xx, yy)))
