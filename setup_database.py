import sqlite3
import random
from datetime import date, timedelta
import os

DB_PATH = "clinic.db"

FIRST_NAMES = [
    "Aarav","Aditi","Ananya","Arjun","Deepak","Divya","Gaurav","Kavya",
    "Kiran","Manish","Meera","Neha","Priya","Rahul","Ravi","Rohit","Sanjay",
    "Shreya","Sunita","Vijay","Pooja","Amit","Anjali","Nikhil","Swati","Ritesh",
    "Pallavi","Harish","Sneha","Vishal","Rekha","Suresh","Geeta","Rajesh","Nisha",
    "Anil","Lakshmi","Mohan","Usha","Pankaj","Shweta","Ramesh","Lata","Manoj",
    "Savita","Dinesh","Sundar","Jaya","Prakash","Leela","Bharat","Radha","Venkat",
    "Geetha","Santosh","Parvati","Naresh","Rukmini","Shankar","Sarita",
]

LAST_NAMES = [
    "Sharma","Verma","Patel","Singh","Kumar","Joshi","Gupta","Mehta",
    "Shah","Rao","Reddy","Nair","Menon","Iyer","Pillai","Agarwal","Tiwari",
    "Mishra","Dubey","Chauhan","Yadav","Pandey","Chaudhary","Desai","Kulkarni",
    "Jain","Bhat","Shetty","Naidu","Rajan","Venkatesh","Krishnan","Subramaniam",
    "Balachandran","Ramachandran","Sundaram","Gopalakrishnan","Viswanathan",
]

CITIES = [
    "Mumbai","Delhi","Bangalore","Hyderabad","Chennai",
    "Pune","Kolkata","Ahmedabad","Jaipur","Lucknow",
]

DOCTORS = [
    ("Dr. Priya Sharma",   "Dermatology",  "Skin & Hair"),
    ("Dr. Rajesh Mehta",   "Dermatology",  "Skin & Hair"),
    ("Dr. Sunita Rao",     "Dermatology",  "Skin & Hair"),
    ("Dr. Arjun Patel",    "Cardiology",   "Heart & Vascular"),
    ("Dr. Meena Iyer",     "Cardiology",   "Heart & Vascular"),
    ("Dr. Vikram Singh",   "Cardiology",   "Heart & Vascular"),
    ("Dr. Anita Desai",    "Orthopedics",  "Bone & Joint"),
    ("Dr. Suresh Joshi",   "Orthopedics",  "Bone & Joint"),
    ("Dr. Kavitha Nair",   "Orthopedics",  "Bone & Joint"),
    ("Dr. Ravi Kumar",     "General",      "General Medicine"),
    ("Dr. Pooja Verma",    "General",      "General Medicine"),
    ("Dr. Deepak Gupta",   "General",      "General Medicine"),
    ("Dr. Lakshmi Pillai", "Pediatrics",   "Child Health"),
    ("Dr. Manish Reddy",   "Pediatrics",   "Child Health"),
    ("Dr. Swati Agarwal",  "Pediatrics",   "Child Health"),
]

TREATMENTS = {
    "Dermatology":  [("Acne Treatment",800,30),("Skin Biopsy",2500,45),("Chemical Peel",3500,60),("Laser Therapy",5000,90),("Patch Test",600,20)],
    "Cardiology":   [("ECG",500,20),("Echocardiogram",3000,45),("Stress Test",2500,60),("Holter Monitor",4000,30),("Cardiac Consultation",1200,30)],
    "Orthopedics":  [("X-Ray",400,15),("Physiotherapy Session",800,45),("Joint Injection",3000,30),("Bone Density Test",2000,30),("Orthopedic Consultation",1000,30)],
    "General":      [("General Checkup",500,20),("Blood Test",700,15),("Urine Analysis",300,10),("Blood Pressure Check",200,10),("Vaccination",600,15)],
    "Pediatrics":   [("Child Wellness Visit",600,30),("Immunization",500,15),("Developmental Screening",1500,45),("Fever Consultation",400,20),("Nutrition Counseling",800,30)],
}

random.seed(42)  # reproducibility


def rand_date(days_ago_max: int, days_ago_min: int = 0) -> str:
    today = date.today()
    delta = random.randint(days_ago_min, days_ago_max)
    return (today - timedelta(days=delta)).isoformat()


def rand_datetime(days_ago_max: int, days_ago_min: int = 0) -> str:
    d = rand_date(days_ago_max, days_ago_min)
    h = random.randint(8, 17)
    m = random.choice([0, 15, 30, 45])
    return f"{d} {h:02d}:{m:02d}:00"


def rand_phone() -> str:
    return f"+91 {random.randint(7000000000, 9999999999)}"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS patients (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name      TEXT NOT NULL,
        last_name       TEXT NOT NULL,
        email           TEXT,
        phone           TEXT,
        date_of_birth   DATE,
        gender          TEXT,
        city            TEXT,
        registered_date DATE
    );
    CREATE TABLE IF NOT EXISTS doctors (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT NOT NULL,
        specialization TEXT,
        department     TEXT,
        phone          TEXT
    );
    CREATE TABLE IF NOT EXISTS appointments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id       INTEGER REFERENCES patients(id),
        doctor_id        INTEGER REFERENCES doctors(id),
        appointment_date DATETIME,
        status           TEXT,
        notes            TEXT
    );
    CREATE TABLE IF NOT EXISTS treatments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id   INTEGER REFERENCES appointments(id),
        treatment_name   TEXT,
        cost             REAL,
        duration_minutes INTEGER
    );
    CREATE TABLE IF NOT EXISTS invoices (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id   INTEGER REFERENCES patients(id),
        invoice_date DATE,
        total_amount REAL,
        paid_amount  REAL,
        status       TEXT
    );
    """)
    conn.commit()


def insert_data(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # ── Doctors ─────────────────────────────────────────────────────────────
    for name, spec, dept in DOCTORS:
        cur.execute(
            "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
            (name, spec, dept, rand_phone() if random.random() > 0.1 else None),
        )
    conn.commit()
    doc_rows = cur.execute("SELECT id, specialization FROM doctors").fetchall()
    doctor_ids   = [r[0] for r in doc_rows]
    doc_spec_map = {r[0]: r[1] for r in doc_rows}

    # ── Patients (200) ───────────────────────────────────────────────────────
    patient_ids = []
    for _ in range(200):
        fn   = random.choice(FIRST_NAMES)
        ln   = random.choice(LAST_NAMES)
        g    = random.choice(["M", "F"])
        dob  = f"{random.randint(1950,2010)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        cur.execute(
            "INSERT INTO patients (first_name,last_name,email,phone,date_of_birth,gender,city,registered_date) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                fn, ln,
                f"{fn.lower()}.{ln.lower()}@email.com" if random.random() > 0.15 else None,
                rand_phone() if random.random() > 0.1 else None,
                dob, g,
                random.choice(CITIES),
                rand_date(365),
            ),
        )
        patient_ids.append(cur.lastrowid)
    conn.commit()

    # ── Appointments (500) ──────────────────────────────────────────────────
    heavy_patients = random.sample(patient_ids, 40)
    statuses       = ["Scheduled", "Completed", "Cancelled", "No-Show"]
    weights        = [0.15, 0.60, 0.15, 0.10]
    completed_ids  = []
    appt_did_map   = {}

    for _ in range(500):
        pid    = random.choice(heavy_patients) if random.random() < 0.35 else random.choice(patient_ids)
        did    = random.choice(doctor_ids)
        status = random.choices(statuses, weights=weights)[0]
        appt_dt = (rand_datetime(0, -30) if status == "Scheduled"
                   else rand_datetime(365, 1))
        cur.execute(
            "INSERT INTO appointments (patient_id,doctor_id,appointment_date,status,notes) VALUES (?,?,?,?,?)",
            (pid, did, appt_dt, status,
             "Follow-up required" if random.random() > 0.7 else None),
        )
        aid = cur.lastrowid
        appt_did_map[aid] = did
        if status == "Completed":
            completed_ids.append(aid)
    conn.commit()

    # ── Treatments (350) linked to completed appointments ───────────────────
    selected = random.sample(completed_ids, min(350, len(completed_ids)))
    for aid in selected:
        spec   = doc_spec_map.get(appt_did_map[aid], "General")
        t_name, t_cost, t_dur = random.choice(TREATMENTS.get(spec, TREATMENTS["General"]))
        cur.execute(
            "INSERT INTO treatments (appointment_id,treatment_name,cost,duration_minutes) VALUES (?,?,?,?)",
            (aid, t_name, round(t_cost * random.uniform(0.8, 1.3), 2), t_dur),
        )
    conn.commit()

    # ── Invoices (300) ───────────────────────────────────────────────────────
    inv_statuses = ["Paid", "Pending", "Overdue"]
    inv_weights  = [0.55, 0.25, 0.20]
    for pid in random.choices(patient_ids, k=300):
        total  = round(random.uniform(200, 8000), 2)
        status = random.choices(inv_statuses, weights=inv_weights)[0]
        paid   = (total if status == "Paid"
                  else round(total * random.uniform(0, 0.5), 2) if status == "Pending"
                  else round(total * random.uniform(0, 0.3), 2))
        cur.execute(
            "INSERT INTO invoices (patient_id,invoice_date,total_amount,paid_amount,status) VALUES (?,?,?,?,?)",
            (pid, rand_date(365), total, paid, status),
        )
    conn.commit()

    # ── Summary ─────────────────────────────────────────────────────────────
    def count(tbl): return cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(
        f"Created {count('patients')} patients, {count('doctors')} doctors, "
        f"{count('appointments')} appointments, {count('treatments')} treatments, "
        f"{count('invoices')} invoices"
    )


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    insert_data(conn)
    conn.close()
    print(f"Database saved to {DB_PATH}")


if __name__ == "__main__":
    main()
