"""
Vanna 2.0 Agent initialisation.

LLM Provider: Google Gemini
  - Model : gemini-2.5-flash
  - Import: from vanna.integrations.google import GeminiLlmService

Environment variables (set in .env21):
  GOOGLE_API_KEY   – your Gemini API key
  GEMINI_MODEL     – optional override, default gemini-2.5-flash
  DB_PATH          – optional override, default clinic.db
"""

import os
from dotenv import load_dotenv

from vanna import Agent, AgentConfig, ToolRegistry
from vanna.core.user.resolver import UserResolver, RequestContext, User
from vanna.tools.run_sql import RunSqlTool
from vanna.tools.visualize_data import VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
)
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.google import GeminiLlmService

load_dotenv(".env21")

DB_PATH = os.getenv("DB_PATH", "clinic.db")

# ── Shared memory instance ──────────────────────────────────────────────────
agent_memory: DemoAgentMemory = DemoAgentMemory()


class DefaultUserResolver(UserResolver):
    """Maps every incoming request to a single default clinic user."""

    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="default_user",
            username="clinic_user",
            email="user@clinic.com",
            group_memberships=["user", "admin"],
        )


def create_agent() -> Agent:
    # 1. LLM Service
    llm_service = GeminiLlmService(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    # 2. Database runner
    sql_runner = SqliteRunner(database_path=DB_PATH)

    # 3. Tool registry
    registry = ToolRegistry()
    registry.register_local_tool(RunSqlTool(sql_runner=sql_runner), access_groups=["user", "admin"])
    registry.register_local_tool(VisualizeDataTool(), access_groups=["user", "admin"])
    registry.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["user", "admin"])
    registry.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["user", "admin"])

    # 4. User resolver
    user_resolver = DefaultUserResolver()

    # 5. Agent config
    config = AgentConfig(
        max_tool_iterations=4,
        stream_responses=False,
        temperature=0.0,
    )

    # 6. Assemble agent
    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=config,
    )

    # 7. Schema context — exact real columns from clinic.db
    schema_context = """
# SCHEMA v5 - CLINIC DATABASE
You are an expert SQL assistant for a CLINIC database.

EXACT table definitions — use ONLY these columns, never invent others:

patients(id INTEGER, first_name TEXT, last_name TEXT, email TEXT, phone TEXT, date_of_birth DATE, gender TEXT, city TEXT, registered_date DATE)
doctors(id INTEGER, name TEXT, specialization TEXT, department TEXT, phone TEXT)
appointments(id INTEGER, patient_id INTEGER, doctor_id INTEGER, appointment_date DATETIME, status TEXT, notes TEXT)
treatments(id INTEGER, appointment_id INTEGER, treatment_name TEXT, cost REAL, duration_minutes INTEGER)
invoices(id INTEGER, patient_id INTEGER, invoice_date DATE, total_amount REAL, paid_amount REAL, status TEXT)

KEY RELATIONSHIPS:
- appointments.patient_id → patients.id
- appointments.doctor_id → doctors.id
- treatments.appointment_id → appointments.id
- invoices.patient_id → patients.id

CRITICAL RULES:
- Patient full name = first_name || ' ' || last_name
- Revenue = treatments.cost — use SUM(t.cost)
- Invoice total = invoices.total_amount
- appointments has NO cost, fee, or price column
- treatments has NO doctor_id — always join via appointments
- appointments.status values: 'scheduled', 'completed', 'cancelled'
- invoices.status values: 'paid', 'unpaid', 'partial'
- NEVER use columns: price, fee, doctor_name, appointment_id on doctors, name on patients
"""

    # 8. Few-shot examples using exact real column names
    few_shots = """
EXACT EXAMPLES — follow these precisely:

Q: Show revenue by doctor
SQL:
SELECT d.name, SUM(t.cost) AS total_revenue
FROM doctors d
JOIN appointments a ON d.id = a.doctor_id
JOIN treatments t ON a.id = t.appointment_id
GROUP BY d.name
ORDER BY total_revenue DESC;

Q: What is total revenue?
SQL:
SELECT SUM(t.cost) AS total_revenue FROM treatments t;

Q: Which doctor has the most appointments?
SQL:
SELECT d.name, COUNT(*) AS num_appointments
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
GROUP BY d.name
ORDER BY num_appointments DESC
LIMIT 1;

Q: How many patients do we have?
SQL:
SELECT COUNT(*) AS total_patients FROM patients;

Q: List all doctors and their specializations
SQL:
SELECT name, specialization, department FROM doctors;

Q: Top 5 patients by spending
SQL:
SELECT p.first_name || ' ' || p.last_name AS patient_name, SUM(t.cost) AS total_spent
FROM patients p
JOIN appointments a ON p.id = a.patient_id
JOIN treatments t ON a.id = t.appointment_id
GROUP BY p.id
ORDER BY total_spent DESC
LIMIT 5;

Q: Show unpaid invoices
SQL:
SELECT p.first_name || ' ' || p.last_name AS patient_name, i.total_amount, i.invoice_date
FROM invoices i
JOIN patients p ON i.patient_id = p.id
WHERE i.status = 'unpaid';

Q: How many cancelled appointments last quarter?
SQL:
SELECT COUNT(*) AS cancelled_count
FROM appointments
WHERE status = 'cancelled'
AND appointment_date >= date('now', '-3 months');

Q: Average treatment cost by specialization
SQL:
SELECT d.specialization, AVG(t.cost) AS avg_cost
FROM doctors d
JOIN appointments a ON d.id = a.doctor_id
JOIN treatments t ON a.id = t.appointment_id
GROUP BY d.specialization;

Q: Which city has the most patients?
SQL:
SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC
LIMIT 1;

Q: Show monthly appointment count for past 6 months
SQL:
SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS total
FROM appointments
WHERE appointment_date >= date('now', '-6 months')
GROUP BY month
ORDER BY month;

Q: Revenue trend by month
SQL:
SELECT strftime('%Y-%m', a.appointment_date) AS month, SUM(t.cost) AS revenue
FROM appointments a
JOIN treatments t ON a.id = t.appointment_id
GROUP BY month
ORDER BY month;

Q: List patients who visited more than 3 times
SQL:
SELECT p.first_name || ' ' || p.last_name AS patient_name, COUNT(*) AS visits
FROM patients p
JOIN appointments a ON p.id = a.patient_id
GROUP BY p.id
HAVING visits > 3
ORDER BY visits DESC;

Q: Show the busiest day of the week for appointments
SQL:
SELECT strftime('%w', appointment_date) AS day_of_week, COUNT(*) AS total
FROM appointments
GROUP BY day_of_week
ORDER BY total DESC;
"""

    # 9. Inject schema via base_prompt — this is the correct hook
    full_prompt = schema_context + "\n\n" + few_shots
    llm_service.system_instruction = full_prompt
    agent.system_prompt_builder.base_prompt = full_prompt

    return agent