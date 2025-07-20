import unittest
import pandas as pd
from data_integrity_suite import StatisticsAnalyzer

class TestStatisticsAnalyzer(unittest.TestCase):

    def setUp(self):
        # Create a dummy dataframe for testing
        data = {
            'OriginalContainerNo': ['CON123', 'CON456', 'CON789', 'CON111'],
            'CorrectedContainerNo': ['CON123', 'CON457', 'CON790', 'CON111'],
            'OriginalLicensePlate': ['LP123', 'LP456', 'LP789', 'LP111'],
            'CorrectedLicensePlate': ['LP123', 'LP456', 'LP790', 'LP112'],
            'OriginalProvince': ['Bangkok', 'Chiang Mai', 'Phuket', 'Pattaya'],
            'CorrectedProvince': ['Bangkok', 'Chiang Mai', 'Phuket', 'Pattaya'],
        }
        self.df = pd.DataFrame(data)
        self.app_config = {
            "column_mapping": {
                "container_number_original": "OriginalContainerNo",
                "container_number_corrected": "CorrectedContainerNo",
                "license_plate_original": "OriginalLicensePlate",
                "license_plate_corrected": "CorrectedLicensePlate",
                "province_original": "OriginalProvince",
                "province_corrected": "CorrectedProvince",
            }
        }

    def test_analyze(self):
        analyzer = StatisticsAnalyzer(self.df, self.app_config)
        report = analyzer.analyze()

        # Check container number stats
        self.assertIn("Analysis for field: 'Container Number'", report)
        self.assertIn("Total Corrections: 2 (50.00%)", report)
        self.assertIn("Distribution of Corrected Values:", report)
        self.assertIn("'CON457': 1 times", report)
        self.assertIn("'CON790': 1 times", report)

        # Check license plate stats
        self.assertIn("Analysis for field: 'License Plate'", report)
        self.assertIn("Total Corrections: 2 (50.00%)", report)
        self.assertIn("'LP790': 1 times", report)
        self.assertIn("'LP112': 1 times", report)

        # Check province stats
        self.assertIn("Analysis for field: 'Province'", report)
        self.assertIn("Total Corrections: 0 (0.00%)", report)


if __name__ == '__main__':
    unittest.main()
