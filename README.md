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

The generated workbook keeps monthly columns in `RawData` for detail analysis and uses a quarterly timeline in the `Chart` sheet.
The GL filter is handled inside Excel (`Chart!B5`) and filters chart values per AD-Mitarbeiter directly from raw answer rows.
The timeframe can be switched directly in Excel via `Chart!B6` between `Quartal` and `Monat`.

## Deployment

- Deploy this folder as a separate Railway service.
- Use private networking between main backend and this service.
