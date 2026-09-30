import unittest
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from app import build_workbook_bytes

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}


def sample_payload():
    rows = []
    for quarter, month, yes, total in [(2, 7, 5, 7), (3, 9, 26, 35)]:
        for index in range(total):
            rows.append({
                "dateKey": f"2026-{month:02d}-08", "dateLabel": f"08.{month:02d}.2026",
                "originalDateKey": f"2026-{month:02d}-08", "originalDateLabel": f"08.{month:02d}.2026",
                "monthKey": f"2026-{month:02d}", "monthLabel": f"{month:02d}.2026",
                "quarterKey": f"2026-Q{quarter}", "quarterLabel": f"Q{quarter} 2026",
                "weekKey": f"2026-W{28 if quarter == 2 else 37}", "weekLabel": f"KW {28 if quarter == 2 else 37} 2026",
                "fragebogenName": f"Perfect Store PET Q{quarter}", "questionId": f"q{quarter}",
                "questionLabel": "Produkt verfügbar?", "analysisQuestionKey": "yesno:produkt verfügbar",
                "analysisQuestionLabel": "Produkt verfügbar?", "distributionsziel": True,
                "answerBoolean": index < yes, "marketName": "Testmarkt", "marketInternalId": "123",
                "chain": "Spar", "glName": "Test GL", "responseId": f"q{quarter}-{index}"
            })
    return {
        "fragebogen": [{"id": "q2", "name": "Perfect Store PET Q2"}, {"id": "q3", "name": "Perfect Store PET Q3"}],
        "selectedQuestions": [{"id": "yesno:produkt verfügbar", "label": "Produkt verfügbar?"}],
        "historicalAnalysis": True, "quarterBasis": "questionnaire",
        "dateRange": {"startDate": "2026-05-01", "endDate": "2026-09-30"}, "rows": rows
    }


class DistributionWorkbookTest(unittest.TestCase):
    def test_chart_axis_uses_distinct_percentage_ticks_and_real_date_range(self):
        with ZipFile(BytesIO(build_workbook_bytes(sample_payload()))) as archive:
            chart = ET.fromstring(archive.read("xl/charts/chart1.xml"))
            axis = chart.find(".//c:valAx", NS)
            self.assertEqual(axis.find("c:numFmt", NS).get("formatCode"), "0.0%")
            self.assertEqual(axis.find("c:majorUnit", NS).get("val"), "0.01")
            strings = archive.read("xl/sharedStrings.xml").decode()
            self.assertIn("01.05.2026 bis 30.09.2026", strings)
            self.assertIn("tatsächliches Antwortdatum", strings)
            self.assertIn("2026-Q2", strings)
            self.assertIn("2026-Q3", strings)
            # Quarterly formulas use the assigned questionnaire quarter, not July's calendar quarter.
            worksheets = "".join(archive.read(name).decode() for name in archive.namelist() if name.startswith("xl/worksheets/sheet"))
            self.assertIn("SUMIFS(RawData!$H:$H,RawData!$C:$C", worksheets)
            self.assertIn("RawTable", archive.read("xl/tables/table1.xml").decode())

    def test_empty_selection_does_not_create_an_empty_chart(self):
        payload = sample_payload()
        payload["rows"] = []
        with ZipFile(BytesIO(build_workbook_bytes(payload))) as archive:
            self.assertNotIn("xl/charts/chart1.xml", archive.namelist())


if __name__ == "__main__":
    unittest.main()
