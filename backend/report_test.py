import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
from app.llm import llm_client  # noqa: E402

for i in range(2):
    t0 = time.time()
    rep = llm_client.generate_report("ENTJ", {"EI": -5.0, "SN": 6.0, "TF": -3.0, "JP": -7.0})
    dt = time.time() - t0
    print(f"--- 报告{i + 1}: {dt:.1f}s")
    print("画像:", rep["portrait"])
    print("优势:", rep["strengths"])
    print("名人:", rep["famous"])
    print("建议:", rep["advice"])
