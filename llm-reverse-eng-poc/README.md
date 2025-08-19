# LLM Reverse Engineering PoC
Automatically analyze a database (schema + sample data), extract metadata, and have an LLM generate a human-friendly technical briefing: entities, relationships, quirks, and potential use cases.

## What you get
- **Schema extraction** via SQLAlchemy reflection (tables, columns, PK/FK, indices).
- **Data profiling** (row counts, null rates, distinct counts, top values, example rows).
- **LLM analysis** that turns raw metadata into:
  - A data dictionary (plain-English column meanings)
  - Candidate ER relationships & cardinalities
  - Potential business KPIs & queries
  - Data quality flags and risks (PII, skew, sparsity, outliers heuristics)
- **Markdown report** saved to `./out/report.md` and a machine-readable JSON to `./out/metadata.json`.

## Quickstart
1. **Install**
   ```bash
   python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure** your database connection in `config.yaml`. Examples are provided for SQLite, Postgres, and MySQL.
   - Set `sampling.max_rows_per_table` to control how much data to sample.
   - Set `llm.provider` and `llm.model`. Defaults target an OpenAI-compatible API, but you can swap in anything by editing `llm_client.py`.

3. **Run**
   ```bash
   python main.py --config config.yaml
   ```

4. **Output**
   - Read `out/report.md` for a compact engineering brief.
   - Open `out/metadata.json` for structured facts you can pipe to other tools.

## Supported Databases
Anything SQLAlchemy supports (SQLite, Postgres, MySQL/MariaDB, etc.).

## Security & Privacy
- By default, only **samples** of data are sent to the LLM (configurable). Remove/obfuscate sensitive columns using `mask.columns` and `mask.rules` in `config.yaml`.
- Set `llm.send_samples: false` to **never** send example values—only schema/profile aggregates.
- The PoC runs locally; only the prompt you allow is sent to your LLM endpoint.

## Files
- `main.py` — orchestrates extract → profile → prompt → report.
- `schema_extractor.py` — schema reflection and profiling.
- `prompt_templates.py` — system/user prompts.
- `llm_client.py` — minimal, swappable client. OpenAI-compatible by default.
- `report_generator.py` — composes Markdown/JSON.
- `config.yaml` — connection & behavior knobs.
- `example_db.py` — creates a tiny SQLite db for demo.

## Demo (no external DB required)
```bash
python example_db.py  # creates demo.sqlite with 3 tables & sample rows
python main.py --config config.yaml --url sqlite:///demo.sqlite
```

## Notes
- Keep `sampling.max_rows_per_table` small for cost control.
- Use a read-only role in production.
- This is a PoC → expect rough edges.
