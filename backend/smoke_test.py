"""E2E 冒烟测试（mock 模式）：注册→答题循环→报告→历史→趋势。"""
import requests

BASE = "http://127.0.0.1:8000/api"
s = requests.Session()

health = s.get(f"{BASE}/health").json()
print("health:", health)
assert health["llm_mode"] == "mock"

r = s.post(f"{BASE}/auth/register", json={"username": "tester", "password": "123456"})
if r.status_code == 400:
    r = s.post(f"{BASE}/auth/login", json={"username": "tester", "password": "123456"})
r.raise_for_status()
token = r.json()["token"]
s.headers["Authorization"] = f"Bearer {token}"
print("auth ok, user:", r.json()["user"])

r = s.post(f"{BASE}/tests")
r.raise_for_status()
data = r.json()
print(f"Q1 [{data['question']['dimension']}]: {data['question']['content'][:30]}...")
print("options:", data["question"]["options"])

answers = ["A", "C", "B", "D", "A", "C", "B", "D", "C", "A", "D", "B", "A", "C", "D", "B", "A", "D", "C", "B"]
i = 0
while data["status"] == "question":
    qid = data["question"]["id"]
    ans = answers[i % len(answers)]
    i += 1
    r = s.post(f"{BASE}/tests/current/answer", json={"question_id": qid, "content": ans})
    r.raise_for_status()
    data = r.json()
    if data["status"] == "question":
        prog = data["progress"]
        conf = {d: prog[d]["confidence"] for d in prog}
        print(f"  answered {ans} -> Q{data['question_num']} [{data['question']['dimension']}] conf={conf}")
    else:
        print(f"  answered {ans} -> completed after {i} questions")

assert data["status"] == "completed", data
report = data["report"]
print("\n===== REPORT =====")
print("type:", report["mbti_type"], report["type_name"])
print("portrait:", report["portrait"][:80], "...")
print("dimensions:")
for d, info in report["dimensions"].items():
    print(f"  {d}: score={info['score']} pole={info['dominant_pole']} ({info['dominant_percent']}%)")
print("strengths:", report["strengths"])

rid = report["id"]
r = s.get(f"{BASE}/reports/{rid}")
r.raise_for_status()
print("\nGET report ok:", r.json()["mbti_type"])

r = s.get(f"{BASE}/reports")
print("report list:", [(x["id"], x["mbti_type"]) for x in r.json()])

# 再测一轮，验证趋势曲线有两点
r = s.post(f"{BASE}/tests")
r.raise_for_status()
data = r.json()
while data["status"] == "question":
    r = s.post(f"{BASE}/tests/current/answer", json={"question_id": data["question"]["id"], "content": "D"})
    r.raise_for_status()
    data = r.json()

r = s.get(f"{BASE}/reports/trend")
trend = r.json()
print("trend points:", [(p["mbti_type"], p["scores"]) for p in trend])
assert len(trend) == 2

# 自由文本评分路径
r = s.post(f"{BASE}/tests")
r.raise_for_status()
data = r.json()
r = s.post(f"{BASE}/tests/current/answer", json={"question_id": data["question"]["id"], "content": "我更喜欢一个人待在家里看书"})
print("\nfree-text answer:", r.json().get("status"), "| next dimension:", r.json().get("question", {}).get("dimension"))

print("\nALL E2E CHECKS PASSED")
