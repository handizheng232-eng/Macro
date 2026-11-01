"""Source-unit and GDP publication-precision regression contracts."""
import unittest
from scripts import refresh_ifind_us_gdp as gdp
from scripts.refresh_ifind_us_late_modules import FRED_SERIES_SPEC


class MacroPrecisionContracts(unittest.TestCase):
    def test_legacy_broad_dollar_uses_official_january_1997_base(self):
        self.assertEqual(FRED_SERIES_SPEC['DTWEXB'][1], '1997年1月=100')
        self.assertEqual(FRED_SERIES_SPEC['DTWEXBGS'][1], '2006年1月=100')

    def test_gdp_rounding_budget_includes_headline_and_four_components(self):
        result = gdp.contribution_rounding_check(3.4, [2.52, 3.27, 0.90, -3.32])
        self.assertEqual(result['componentSum'], 3.37)
        self.assertEqual(result['residualPp'], -0.03)
        self.assertEqual(result['tolerancePp'], 0.07)
        self.assertEqual(result['headlineResolutionPp'], 0.1)
        self.assertEqual(result['componentResolutionPp'], 0.01)
        self.assertTrue(result['passed'])
        self.assertFalse(gdp.contribution_rounding_check(3.4, [2.52, 3.27, 0.90, -3.21])['passed'])

    def test_rounding_budget_rejects_missing_nonfinite_or_undeclared_precision(self):
        for components in [[1, 2, 3], [1, 2, 3, float('nan')], [1, 2, 3, 0.001]]:
            with self.assertRaises(ValueError):
                gdp.contribution_rounding_check(3.4, components)
        with self.assertRaises(ValueError):
            gdp.contribution_rounding_check(3.41, [1, 1, 1, 0.4])


if __name__ == '__main__':
    unittest.main()
