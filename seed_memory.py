"""
Seed DemoAgentMemory with 15 known-good question → SQL pairs.

Vanna 2.0 learns from successful interactions stored in DemoAgentMemory.
Running this script before starting the API gives the agent a head start
so it can find similar past queries and generate better SQL immediately.

Usage:
    python seed_memory.py
"""

import asyncio
from vanna_setup import agent_memory

# ── 15 seed Q&A pairs covering all required categories ──────────────────────
SEED_PAIRS = [
    # Patient queries
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients",
    },
    {
        "question": "List patients by city",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients "
            "GROUP BY city "
            "ORDER BY patient_count DESC"
        ),
    },
    {
        "question": "Show female patients",
        "sql": (
            "SELECT first_name, last_name, email, city "
            "FROM patients "
            "WHERE gender = 'F' "
            "ORDER BY last_name"
        ),
    },

    # Doctor queries
    {
        "question": "List all doctors and their specializations",
        "sql": (
            "SELECT name, specialization, department "
            "FROM doctors "
            "ORDER BY specialization, name"
        ),
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": (
            "SELECT d.name, COUNT(*) AS appointment_count "
            "FROM appointments a "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY appointment_count DESC "
            "LIMIT 1"
        ),
    },

    # Appointment queries
    {
        "question": "Show me appointments for last month",
        "sql": (
            "SELECT a.id, p.first_name || ' ' || p.last_name AS patient, "
            "d.name AS doctor, a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors  d ON d.id = a.doctor_id "
            "WHERE strftime('%Y-%m', a.appointment_date) = "
            "      strftime('%Y-%m', date('now', '-1 month')) "
            "ORDER BY a.appointment_date"
        ),
    },
    {
        "question": "How many cancelled appointments last quarter?",
        "sql": (
            "SELECT COUNT(*) AS cancelled_count "
            "FROM appointments "
            "WHERE status = 'Cancelled' "
            "  AND appointment_date >= date('now', '-3 months')"
        ),
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": (
            "SELECT strftime('%Y-%m', appointment_date) AS month, "
            "       COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month "
            "ORDER BY month"
        ),
    },

    # Financial queries
    {
        "question": "What is the total revenue?",
        "sql": "SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices",
    },
    {
        "question": "Show revenue by doctor",
        "sql": (
            "SELECT d.name, ROUND(SUM(i.total_amount), 2) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors      d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY total_revenue DESC"
        ),
    },
    {
        "question": "Show unpaid invoices",
        "sql": (
            "SELECT p.first_name || ' ' || p.last_name AS patient, "
            "       i.invoice_date, i.total_amount, "
            "       ROUND(i.total_amount - i.paid_amount, 2) AS balance_due, "
            "       i.status "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.invoice_date"
        ),
    },
    {
        "question": "Top 5 patients by spending",
        "sql": (
            "SELECT p.first_name || ' ' || p.last_name AS patient, "
            "       ROUND(SUM(i.total_amount), 2) AS total_spending "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id "
            "ORDER BY total_spending DESC "
            "LIMIT 5"
        ),
    },
    {
        "question": "Average treatment cost by specialization",
        "sql": (
            "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors      d ON d.id = a.doctor_id "
            "GROUP BY d.specialization "
            "ORDER BY avg_cost DESC"
        ),
    },

    # Time-based queries
    {
        "question": "Which city has the most patients?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients "
            "GROUP BY city "
            "ORDER BY patient_count DESC "
            "LIMIT 1"
        ),
    },
    {
        "question": "What percentage of appointments are no-shows?",
        "sql": (
            "SELECT ROUND("
            "  100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2"
            ") AS no_show_percentage "
            "FROM appointments"
        ),
    },
]


async def seed() -> None:
    print("Seeding agent memory with 15 Q&A pairs …\n")
    for pair in SEED_PAIRS:
        await agent_memory.save_tool_usage(
            question=pair["question"],
            tool_name="run_sql",
            args={"sql": pair["sql"]},
            context=None,   # type: ignore[arg-type]
            success=True,
            metadata={"seeded": True, "source": "seed_memory.py"},
        )
        print(f"  ✓ {pair['question'][:65]}")

    total = len(agent_memory._memories)
    print(f"\nTotal memories stored: {total}")
    print("Memory seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
