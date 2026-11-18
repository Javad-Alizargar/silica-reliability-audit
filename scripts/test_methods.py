"""Hand-computed mathematical checks, independent of empirical outcomes."""
import unittest
import numpy as np
from analyze import conformal_quantile, prediction_set, calibrate

class MethodTests(unittest.TestCase):
    def test_finite_sample_rank(self):
        self.assertEqual(conformal_quantile([.1,.2,.3,.4],.4),.3)
        self.assertTrue(np.isinf(conformal_quantile([.1,.2,.3,.4],.1)))
    def test_label_membership(self):
        np.testing.assert_array_equal(prediction_set([.1,.5,.9],.2),[1,0,2])
        np.testing.assert_array_equal(prediction_set([.1,.5,.9],.9),[3,3,3])
    def test_study_max_units(self):
        q=calibrate([0,0,1,1],np.array([.1,.7,.8,.1]),["a","a","b","b"],123)
        self.assertEqual(q[("study_max",.2)][1],2)
        self.assertEqual(q[("pooled",.2)][0],.9)
        self.assertTrue(np.isinf(q[("study_max",.2)][0]))
    def test_calibration_order_independence_for_max(self):
        x=calibrate([0,1,0],np.array([.1,.8,.3]),["a","b","a"],5)
        y=calibrate([0,0,1],np.array([.3,.1,.8]),["a","a","b"],5)
        self.assertEqual(x[("study_max",.1)],y[("study_max",.1)])

if __name__=="__main__":unittest.main()
