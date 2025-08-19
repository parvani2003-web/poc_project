from __future__ import annotations
import argparse, json, yaml, os
from sqlalchemy import create_engine
from schema_extractor import SchemaExtractor
from report_generator import generate_report

def load_cfg(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    ap = argparse.ArgumentParser(description="LLM Reverse Engineering PoC")
    ap.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    ap.add_argument("--url", default=None, help="SQLAlchemy database URL (overrides config)")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    if args.url:
        db_url = args.url
    else:
        db_url = cfg.get("connection", {}).get("url")
    assert db_url, "Database URL must be provided via --url or config.connection.url"

    engine = create_engine(db_url, pool_pre_ping=True)
    extractor = SchemaExtractor(engine, cfg)
    metadata = extractor.run()

    outdir = cfg.get("output", {}).get("dir", "out")
    llm_cfg = cfg.get("llm", {})

    # Optionally drop samples before LLM if send_samples=false
    if not llm_cfg.get("send_samples", True):
        for t in metadata.get("tables", []):
            for c in t.get("columns", []):
                c["samples"] = []

    res = generate_report(metadata, outdir, llm_cfg)
    print("Wrote:", res["report_path"])
    print("Meta :", res["metadata_path"])

if __name__ == "__main__":
    main()
