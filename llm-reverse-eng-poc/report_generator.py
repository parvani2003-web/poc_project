from __future__ import annotations
import json, os
from typing import Dict, Any
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from llm_client import LLMClient

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def generate_report(metadata: Dict[str, Any], outdir: str, llm_cfg: Dict[str, Any]):
    ensure_dir(outdir)
    metadata_path = os.path.join(outdir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    user_prompt = USER_PROMPT_TEMPLATE.format(metadata_json=json.dumps(metadata, ensure_ascii=False, indent=2))

    client = LLMClient(
        provider=llm_cfg.get("provider","openai"),
        model=llm_cfg.get("model","gpt-4o-mini"),
        temperature=float(llm_cfg.get("temperature", 0.2)),
        max_tokens=int(llm_cfg.get("max_tokens", 2000)),
    )
    text = client.generate(SYSTEM_PROMPT, user_prompt)

    out_md = os.path.join(outdir, "report.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(text)

    return {"report_path": out_md, "metadata_path": metadata_path}
