import json
from flask import Flask, render_template, request
from openai import OpenAI, RateLimitError

from db_xampp import apply_ddl, run_select_reports, seed_demo_data, list_tables

client = OpenAI()
app = Flask(__name__)


def build_project_description(form_data: dict) -> str:
    return f"""
Domain: {form_data.get('domain', '').strip()}
Primary Entity Focus: {form_data.get('primary_entity', '').strip()}
Constraint/Rule: {form_data.get('constraint_rule', '').strip()}
Advanced Feature: {form_data.get('advanced_feature', '').strip()}
Security/Access Control: {form_data.get('security', '').strip()}
Reporting Requirement: {form_data.get('reporting', '').strip()}
Common Tasks: {form_data.get('common_tasks', '').strip()}
""".strip()


def build_main_prompt(project_description: str) -> str:
    # ✅ tables_3nf alanını UI ile uyumlu olacak şekilde ZORUNLU yaptık (name + columns)
    return f"""
Aşağıda bir veritabanı projesi için açıklama var.

İSTEKLER:
1) İş kuralları (business rules) üret.
2) E/A/R/C bileşenlerini çıkar (Entities, Attributes, Relationships, Constraints).
3) Normalleştirilmiş (3NF) tablo listesini VER ve HER TABLO için kolonları detaylandır.
4) MySQL/MariaDB uyumlu SQL DDL (CREATE TABLE) yaz.
5) En az 3 rapor sorgusu (SELECT) öner (mevcut tablolarla uyumlu).
6) Kısa reflection yaz.

ÖNEMLİ:
- SQL DDL MUTLAKA MySQL / MariaDB (XAMPP) uyumlu olmalı.
- AUTO_INCREMENT, VARCHAR, INT, DATETIME kullan.
- Likes tablosunda (UserID, PostID) UNIQUE olmalı.
- Posts için index: (UserID, CreatedAt)

ÇIKTIYI SADECE JSON OLARAK DÖN (Markdown yok).

JSON ŞEMASI:
{{
  "project_summary": "Kısa ve teknik olmayan proje özeti.",
  "business_rules": [
    {{
      "BR_ID": "BR-01",
      "type": "S/T/O/Y",
      "rule": "Kural cümlesi",
      "er_effect": "E/R/A/C",
      "implementation_hint": "Nasıl uygulanır?",
      "rationale": "Neden gerekli?"
    }}
  ],
  "earc": {{
    "entities": [
      {{
        "name": "Users",
        "attributes": ["UserID (PK)", "Username", "Email", "CreatedAt"]
      }}
    ],
    "relationships": [
      "Users 1..N Posts",
      "Users 1..N Comments",
      "Users 1..N Likes",
      "Posts 1..N Comments",
      "Posts 1..N Likes"
    ],
    "constraints": [
      "Likes(UserID, PostID) benzersiz olmalı"
    ]
  }},
  "tables_3nf": [
    {{
      "name": "Users",
      "columns": [
        {{"name":"UserID","type":"INT","constraints":"PK, AUTO_INCREMENT"}},
        {{"name":"Username","type":"VARCHAR(50)","constraints":"NOT NULL"}},
        {{"name":"Email","type":"VARCHAR(100)","constraints":"NOT NULL"}},
        {{"name":"CreatedAt","type":"DATETIME","constraints":"DEFAULT CURRENT_TIMESTAMP"}}
      ]
    }}
  ],
  "sql": {{
    "ddl": "Burada MySQL uyumlu CREATE TABLE komutları tek string olarak.",
    "extra_objects": [
      "INDEX/VIEW/TRIGGER gibi öneriler"
    ],
    "reports": [
      "SELECT ... ;",
      "SELECT ... ;"
    ]
  }},
  "reflection": "Kısa yansıtma paragrafı."
}}

Proje açıklaması:
{project_description}
""".strip()


def call_chatgpt(prompt: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return STRICT JSON only. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    raw_text = response.choices[0].message.content.strip()

    # ```json ... ``` temizliği
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").replace("json", "", 1).strip()

    return json.loads(raw_text)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    form_data = {
        "domain": request.form.get("domain", ""),
        "primary_entity": request.form.get("primary_entity", ""),
        "constraint_rule": request.form.get("constraint_rule", ""),
        "advanced_feature": request.form.get("advanced_feature", ""),
        "security": request.form.get("security", ""),
        "reporting": request.form.get("reporting", ""),
        "common_tasks": request.form.get("common_tasks", ""),
    }

    project_description = build_project_description(form_data)
    prompt = build_main_prompt(project_description)

    # 1) OpenAI sonucu
    try:
        result_json = call_chatgpt(prompt)
    except RateLimitError as e:
        result_json = {"error": f"OpenAI quota/rate limit: {e}"}
    except Exception as e:
        result_json = {"error": f"OpenAI error: {e}"}

    ddl_executed, ddl_errors, report_outputs = [], [], []
    seed_info = {"seeded": False, "reason": "Çalıştırılmadı"}
    tables_now = []

    try:
        sql_block = result_json.get("sql", {}) if isinstance(result_json, dict) else {}
        ddl_sql = (sql_block or {}).get("ddl", "")
        reports = (sql_block or {}).get("reports", [])

        # 2) DDL uygula
        if isinstance(ddl_sql, str) and ddl_sql.strip():
            ddl_executed, ddl_errors = apply_ddl(ddl_sql)

        # DB tablolarını gör
        tables_now = list_tables()

        # 3) ✅ önce seed
        seed_info = seed_demo_data()

        # 4) ✅ sonra raporlar
        if isinstance(reports, list) and reports:
            report_outputs = run_select_reports(reports, max_rows=50)

    except Exception as e:
        ddl_errors.append({"statement": "SYSTEM", "error": str(e)})

    return render_template(
        "results.html",
        project_description=project_description,
        result=result_json,
        ddl_executed=ddl_executed,
        ddl_errors=ddl_errors,
        report_outputs=report_outputs,
        seed_info=seed_info,
        tables_now=tables_now
    )


if __name__ == "__main__":
    app.run(debug=True)
