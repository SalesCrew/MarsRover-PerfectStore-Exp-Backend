import unittest
from copy import deepcopy
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


def single_quarter_payload():
    payload = sample_payload()
    payload["fragebogen"] = [payload["fragebogen"][1]]
    payload["historicalAnalysis"] = False
    payload["selectedQuestions"] = [{"id": "q3", "label": "Produkt verfügbar?"}]
    payload["dateRange"] = {"startDate": "2026-07-10", "endDate": "2026-09-30"}
    payload["rows"] = [row for row in payload["rows"] if row["quarterKey"] == "2026-Q3"]
    for index, row in enumerate(payload["rows"]):
        month, week = (8, 32) if index < 17 else (9, 37)
        row.update({
            "dateKey": f"2026-{month:02d}-08", "dateLabel": f"08.{month:02d}.2026",
            "originalDateKey": f"2026-{month:02d}-08", "originalDateLabel": f"08.{month:02d}.2026",
            "monthKey": f"2026-{month:02d}", "monthLabel": f"{month:02d}.2026",
            "weekKey": f"2026-W{week}", "weekLabel": f"KW {week} 2026",
        })
    return payload


def worksheet_cells(archive, name):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    sheet_names = [sheet.get("name") for sheet in workbook.find("m:sheets", NS)]
    sheet_number = sheet_names.index(name) + 1
    worksheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet_number}.xml"))
    strings = ["".join(item.itertext()) for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
    cells = {}
    for cell in worksheet.findall(".//m:sheetData/m:row/m:c", NS):
        value = cell.find("m:v", NS)
        formula = cell.find("m:f", NS)
        cells[cell.get("r")] = (
            formula.text if formula is not None else
            strings[int(value.text)] if cell.get("t") == "s" else
            value.text if value is not None else None
        )
    return cells


class DistributionWorkbookTest(unittest.TestCase):
    def test_chart_axis_has_percentage_bounds_readable_ticks_and_real_date_range(self):
        with ZipFile(BytesIO(build_workbook_bytes(sample_payload()))) as archive:
            chart = ET.fromstring(archive.read("xl/charts/chart1.xml"))
            axis = chart.find(".//c:valAx", NS)
            self.assertEqual(axis.find("c:numFmt", NS).get("formatCode"), "0.0%")
            minimum = float(axis.find("c:scaling/c:min", NS).get("val"))
            maximum = float(axis.find("c:scaling/c:max", NS).get("val"))
            interval = float(axis.find("c:majorUnit", NS).get("val"))
            self.assertEqual((minimum, maximum), (0, 1))
            self.assertLessEqual((maximum - minimum) / interval, 10)
            strings = archive.read("xl/sharedStrings.xml").decode()
            self.assertIn("01.05.2026 bis 30.09.2026", strings)
            self.assertIn("tatsächliches Antwortdatum", strings)
            self.assertIn("2026-Q2", strings)
            self.assertIn("2026-Q3", strings)
            # Quarterly formulas use the assigned questionnaire quarter, not July's calendar quarter.
            worksheets = "".join(archive.read(name).decode() for name in archive.namelist() if name.startswith("xl/worksheets/sheet"))
            self.assertIn("SUMIFS(RawData!$H:$H,RawData!$C:$C", worksheets)
            self.assertIn("RawTable", archive.read("xl/tables/table1.xml").decode())

    def test_filtered_single_quarter_starts_weekly_and_can_switch_to_months(self):
        with ZipFile(BytesIO(build_workbook_bytes(single_quarter_payload()))) as archive:
            self.assertEqual(worksheet_cells(archive, "Chart")["B7"], "KW")
            options = worksheet_cells(archive, "Lists")
            self.assertEqual([options[f"D{row}"] for row in range(1, 4)], ["Quartal", "Monat", "KW"])
            data = worksheet_cells(archive, "ChartData")
            self.assertEqual([data["G2"], data["G3"]], ["2026-W32", "2026-W37"])
            self.assertEqual([data["P2"], data["P3"]], ["2026-08", "2026-09"])
            # Single-questionnaire month totals must use the original question column.
            self.assertIn("RawData!$G:$G", data["R2"])
            self.assertIn("RawData!$A:$A", data["S2"])
            self.assertIn('Chart!$B$7="Monat"', data["M2"])
            self.assertIn('INDEX($T$2:$T$3', data["N2"])
            self.assertEqual(data["A2"], "2026-Q3")

    def test_default_preserves_quarterly_overview_and_explicit_compression(self):
        cases = {
            "unfiltered": single_quarter_payload(),
            "multiple_quarters": sample_payload(),
            "compressed": single_quarter_payload(),
            "start_only": single_quarter_payload(),
            "end_only": single_quarter_payload(),
        }
        cases["unfiltered"]["dateRange"] = {}
        cases["compressed"]["quarterCompression"] = {"enabled": True, "year": 2026, "quarter": 3}
        del cases["start_only"]["dateRange"]["endDate"]
        del cases["end_only"]["dateRange"]["startDate"]
        for name, payload in cases.items():
            with self.subTest(name=name), ZipFile(BytesIO(build_workbook_bytes(deepcopy(payload)))) as archive:
                expected = "KW" if name in ("start_only", "end_only") else "Quartal"
                self.assertEqual(worksheet_cells(archive, "Chart")["B7"], expected)

    def test_months_remain_available_without_week_keys(self):
        payload = single_quarter_payload()
        for row in payload["rows"]:
            row.pop("weekKey")
            row.pop("weekLabel")
        with ZipFile(BytesIO(build_workbook_bytes(payload))) as archive:
            self.assertEqual(worksheet_cells(archive, "Chart")["B7"], "Quartal")
            data = worksheet_cells(archive, "ChartData")
            self.assertEqual([data["P2"], data["P3"]], ["2026-08", "2026-09"])
            chart = ET.fromstring(archive.read("xl/charts/chart1.xml"))
            self.assertEqual(chart.find(".//c:cat//c:f", NS).text, "ChartData!$M$2:$M$3")

    def test_empty_selection_does_not_create_an_empty_chart(self):
        payload = sample_payload()
        payload["rows"] = []
        with ZipFile(BytesIO(build_workbook_bytes(payload))) as archive:
            self.assertNotIn("xl/charts/chart1.xml", archive.namelist())


if __name__ == "__main__":
    unittest.main()
