from __future__ import annotations
import re, json, math, time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from tqdm import tqdm

@dataclass
class ColumnProfile:
    name: str
    type: str
    nullable: bool
    default: Optional[str]
    is_primary_key: bool
    is_foreign_key: bool
    fk_target: Optional[str]
    samples: List[Any]
    null_count: int
    row_count: int
    distinct_count: Optional[int]
    top_values: List[Tuple[Any, int]]
    min_value: Optional[Any]
    max_value: Optional[Any]
    avg_length: Optional[float]

    def to_dict(self):
        d = asdict(self)
        # convert non-JSONable values
        d["samples"] = [str(x) if x is not None else None for x in self.samples]
        d["top_values"] = [(str(v) if v is not None else None, int(c)) for v, c in self.top_values]
        return d

@dataclass
class TableProfile:
    name: str
    row_count: int
    columns: List[ColumnProfile]
    foreign_keys: List[Dict[str, Any]]

    def to_dict(self):
        return {
            "name": self.name,
            "row_count": self.row_count,
            "columns": [c.to_dict() for c in self.columns],
            "foreign_keys": self.foreign_keys,
        }

class SchemaExtractor:
    def __init__(self, engine: Engine, cfg: Dict[str, Any]):
        self.engine = engine
        self.inspector = inspect(engine)
        self.cfg = cfg

    def _limit(self, tbl: str) -> int:
        return int(self.cfg.get("sampling", {}).get("max_rows_per_table", 100))

    def _mask_value(self, col: str, v: Any) -> Any:
        if v is None:
            return None
        masks = self.cfg.get("mask", {})
        blocked_cols = set([c.lower() for c in masks.get("columns", [])])
        if col.lower() in blocked_cols:
            return "[REDACTED]"
        s = str(v)
        for rule in masks.get("rules", []):
            pattern = re.compile(rule["pattern"], flags=getattr(re, rule.get("flags",""), 0))
            s = pattern.sub(rule.get("replace","[REDACTED]"), s)
        return s

    def profile_table(self, table: str) -> TableProfile:
        columns = self.inspector.get_columns(table)
        fks = self.inspector.get_foreign_keys(table)
        pk_cols = set(self.inspector.get_pk_constraint(table).get("constrained_columns") or [])

        # row count
        with self.engine.connect() as conn:
            try:
                rc = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            except Exception:
                rc = None

        col_profiles: List[ColumnProfile] = []

        for col in columns:
            name = col["name"]
            coltype = str(col["type"])
            nullable = bool(col.get("nullable", True))
            default = col.get("default")
            is_pk = name in pk_cols

            fk_target = None
            is_fk = False
            for fk in fks:
                if name in (fk.get("constrained_columns") or []):
                    is_fk = True
                    referred = fk.get("referred_table")
                    referred_cols = fk.get("referred_columns") or []
                    fk_target = f"{referred}({', '.join(referred_cols)})" if referred else None

            # sample values
            lim = self._limit(table)
            samples = []
            null_count = 0
            distinct_count = None
            top_values = []
            min_value = None
            max_value = None
            avg_length = None

            with self.engine.connect() as conn:
                try:
                    result = conn.execute(text(f"SELECT {name} FROM {table} LIMIT {lim}"))
                    vals = [row[0] for row in result.fetchall()]
                    samples = [self._mask_value(name, v) for v in vals]
                except Exception:
                    samples = []

                try:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {name} IS NULL"))
                    null_count = res.scalar_one()
                except Exception:
                    null_count = 0

                # distinct & top-k
                try:
                    res = conn.execute(text(f"SELECT COUNT(DISTINCT {name}) FROM {table}"))
                    distinct_count = res.scalar_one()
                    if distinct_count is not None and distinct_count <= int(self.cfg["sampling"]["max_distinct_for_topk"]):
                        res = conn.execute(text(f"SELECT {name}, COUNT(*) c FROM {table} GROUP BY {name} ORDER BY c DESC LIMIT :k"), {"k": int(self.cfg["sampling"]["topk"])})
                        top_values = [(self._mask_value(name, r[0]), int(r[1])) for r in res.fetchall()]
                except Exception:
                    distinct_count = None

                # min/max for numeric/date-ish
                for agg, target in [("MIN", "min_value"), ("MAX", "max_value")]:
                    try:
                        res = conn.execute(text(f"SELECT {agg}({name}) FROM {table}"))
                        val = res.scalar_one()
                        if target == "min_value":
                            min_value = self._mask_value(name, val)
                        else:
                            max_value = self._mask_value(name, val)
                    except Exception:
                        pass

                # average text length
                if self.cfg.get("sampling", {}).get("infer_text_lengths", True):
                    try:
                        res = conn.execute(text(f"SELECT AVG(LENGTH(CAST({name} AS TEXT))) FROM {table}"))
                        avglen = res.scalar()
                        avg_length = float(avglen) if avglen is not None else None
                    except Exception:
                        avg_length = None

            cp = ColumnProfile(
                name=name,
                type=coltype,
                nullable=nullable,
                default=str(default) if default is not None else None,
                is_primary_key=is_pk,
                is_foreign_key=is_fk,
                fk_target=fk_target,
                samples=samples,
                null_count=int(null_count),
                row_count=int(rc) if rc is not None else 0,
                distinct_count=int(distinct_count) if distinct_count is not None else None,
                top_values=top_values,
                min_value=min_value,
                max_value=max_value,
                avg_length=avg_length,
            )
            col_profiles.append(cp)

        tprof = TableProfile(
            name=table,
            row_count=int(rc) if rc is not None else 0,
            columns=col_profiles,
            foreign_keys=fks,
        )
        return tprof

    def run(self) -> Dict[str, Any]:
        tables = [t for t in self.inspector.get_table_names() if not t.startswith("sqlite_")]
        profiles = []
        for t in tqdm(tables, desc="Profiling tables"):
            profiles.append(self.profile_table(t))

        return {
            "tables": [p.to_dict() for p in profiles],
            "generated_at": pd.Timestamp.utcnow().isoformat(),
        }
