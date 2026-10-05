# Perfectstore Export Backend

Dedicated Python service for Excel export generation.

## Endpoints

- `GET /health`
- `POST /distribution-export.xlsx`

## Local run

```bash
python -m pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Payload contract

The `POST /distribution-export.xlsx` endpoint accepts the normalized export payload built in the main backend and returns raw `.xlsx` bytes.

The generated workbook keeps monthly columns in `RawData` for detail analysis.
The GL filter is handled inside Excel (`Chart!B5`) and filters chart values per AD-Mitarbeiter directly from raw answer rows.
For exports containing multiple Fragebögen, copied Ja/Nein questions are grouped by normalized wording while their original IDs remain visible in `RawData`.
The timeframe can be switched directly in Excel via `Chart!B7`; all exports support
`Monat`, `Quartal`, and `KW`, including single-Fragebogen exports. A date-filtered
export containing one reporting quarter starts with `KW` when weekly data is
available. Other exports, including quarter-compressed exports, start with `Quartal`.

The app can prefilter by an optional beginning/end date. The main backend filters the
original completion date in `Europe/Vienna`, including both boundary days, before
applying any quarter compression. The selected range is shown in the `Chart` sheet.
Perfect Store reporting quarters follow the questionnaire's quarter (including
extensions such as Q2 until July 10); month/week views retain the actual response date.
The chart's percentage axis uses one decimal, a fixed 0–100% range, and
ten-percentage-point tick intervals.

## Deployment

- Deploy this folder as a separate Railway service.
- Use private networking between main backend and this service.
