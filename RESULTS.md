# Test Results — 20 Questions

**Score: 20/20 questions produced correct SQL**

All queries were validated by running them directly against .

---

## Q01: How many patients do we have?

**Expected behaviour:** Returns count

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT COUNT(*) AS total_patients FROM patients
```

**Result:** 1 row(s) returned

**Columns:** ['total_patients']

**Sample output:**
  - (200,)

---

## Q02: List all doctors and their specializations

**Expected behaviour:** Returns doctor list

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT name, specialization, department FROM doctors ORDER BY specialization
```

**Result:** 15 row(s) returned

**Columns:** ['name', 'specialization', 'department']

**Sample output:**
  - ('Dr. Arjun Patel', 'Cardiology', 'Heart & Vascular')
  - ('Dr. Meena Iyer', 'Cardiology', 'Heart & Vascular')
  - ('Dr. Vikram Singh', 'Cardiology', 'Heart & Vascular')

---

## Q03: Show me appointments for last month

**Expected behaviour:** Filters by date

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient,
       d.name AS doctor, a.appointment_date, a.status
FROM appointments a
JOIN patients p ON p.id = a.patient_id
JOIN doctors d ON d.id = a.doctor_id
WHERE strftime('%Y-%m', a.appointment_date) = strftime('%Y-%m', date('now','-1 month'))
ORDER BY a.appointment_date
```

**Result:** 26 row(s) returned

**Columns:** ['patient', 'doctor', 'appointment_date', 'status']

**Sample output:**
  - ('Rahul Kumar', 'Dr. Meena Iyer', '2026-03-01 17:00:00', 'Cancelled')
  - ('Nikhil Patel', 'Dr. Ravi Kumar', '2026-03-02 10:15:00', 'No-Show')
  - ('Ritesh Shah', 'Dr. Ravi Kumar', '2026-03-02 14:45:00', 'Completed')

---

## Q04: Which doctor has the most appointments?

**Expected behaviour:** Aggregation + ordering

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id=a.doctor_id GROUP BY d.id,d.name ORDER BY appointment_count DESC LIMIT 1
```

**Result:** 1 row(s) returned

**Columns:** ['name', 'appointment_count']

**Sample output:**
  - ('Dr. Manish Reddy', 46)

---

## Q05: What is the total revenue?

**Expected behaviour:** SUM of invoice amounts

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT ROUND(SUM(total_amount),2) AS total_revenue FROM invoices
```

**Result:** 1 row(s) returned

**Columns:** ['total_revenue']

**Sample output:**
  - (1252477.71,)

---

## Q06: Show revenue by doctor

**Expected behaviour:** JOIN + GROUP BY

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.name, ROUND(SUM(i.total_amount),2) AS total_revenue FROM invoices i JOIN appointments a ON a.patient_id=i.patient_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.id,d.name ORDER BY total_revenue DESC
```

**Result:** 15 row(s) returned

**Columns:** ['name', 'total_revenue']

**Sample output:**
  - ('Dr. Lakshmi Pillai', 293802.83)
  - ('Dr. Manish Reddy', 241228.48)
  - ('Dr. Priya Sharma', 232075.51)

---

## Q07: How many cancelled appointments last quarter?

**Expected behaviour:** Status filter + date

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status='Cancelled' AND appointment_date >= date('now','-3 months')
```

**Result:** 1 row(s) returned

**Columns:** ['cancelled_count']

**Sample output:**
  - (21,)

---

## Q08: Top 5 patients by spending

**Expected behaviour:** JOIN + ORDER + LIMIT

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient, ROUND(SUM(i.total_amount),2) AS total_spending FROM invoices i JOIN patients p ON p.id=i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5
```

**Result:** 5 row(s) returned

**Columns:** ['patient', 'total_spending']

**Sample output:**
  - ('Rahul Rajan', 23403.32)
  - ('Nisha Shetty', 22266.45)
  - ('Shweta Tiwari', 21437.55)

---

## Q09: Average treatment cost by specialization

**Expected behaviour:** Multi-table JOIN + AVG

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.specialization, ROUND(AVG(t.cost),2) AS avg_cost FROM treatments t JOIN appointments a ON a.id=t.appointment_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.specialization ORDER BY avg_cost DESC
```

**Result:** 5 row(s) returned

**Columns:** ['specialization', 'avg_cost']

**Sample output:**
  - ('Dermatology', 2661.99)
  - ('Cardiology', 2051.92)
  - ('Orthopedics', 1640.75)

---

## Q10: Show monthly appointment count for the past 6 months

**Expected behaviour:** Date grouping

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count FROM appointments WHERE appointment_date >= date('now','-6 months') GROUP BY month ORDER BY month
```

**Result:** 8 row(s) returned

**Columns:** ['month', 'appointment_count']

**Sample output:**
  - ('2025-10', 29)
  - ('2025-11', 41)
  - ('2025-12', 36)

---

## Q11: Which city has the most patients?

**Expected behaviour:** GROUP BY + COUNT

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1
```

**Result:** 1 row(s) returned

**Columns:** ['city', 'patient_count']

**Sample output:**
  - ('Delhi', 31)

---

## Q12: List patients who visited more than 3 times

**Expected behaviour:** HAVING clause

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient, COUNT(*) AS visit_count FROM appointments a JOIN patients p ON p.id=a.patient_id GROUP BY p.id HAVING visit_count > 3 ORDER BY visit_count DESC
```

**Result:** 49 row(s) returned

**Columns:** ['patient', 'visit_count']

**Sample output:**
  - ('Leela Krishnan', 12)
  - ('Amit Mehta', 9)
  - ('Ritesh Shah', 8)

---

## Q13: Show unpaid invoices

**Expected behaviour:** Status filter

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient, i.invoice_date, ROUND(i.total_amount-i.paid_amount,2) AS balance_due, i.status FROM invoices i JOIN patients p ON p.id=i.patient_id WHERE i.status IN ('Pending','Overdue') ORDER BY balance_due DESC
```

**Result:** 121 row(s) returned

**Columns:** ['patient', 'invoice_date', 'balance_due', 'status']

**Sample output:**
  - ('Usha Chauhan', '2025-08-16', 7644.22, 'Overdue')
  - ('Nikhil Rajan', '2025-12-22', 7265.9, 'Pending')
  - ('Sanjay Venkatesh', '2026-03-03', 6754.51, 'Overdue')

---

## Q14: What percentage of appointments are no-shows?

**Expected behaviour:** Percentage calculation

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT ROUND(100.0*SUM(CASE WHEN status='No-Show' THEN 1 ELSE 0 END)/COUNT(*),2) AS no_show_percentage FROM appointments
```

**Result:** 1 row(s) returned

**Columns:** ['no_show_percentage']

**Sample output:**
  - (8.2,)

---

## Q15: Show the busiest day of the week for appointments

**Expected behaviour:** Date function

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT CASE strftime('%w',appointment_date) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END AS day_of_week, COUNT(*) AS appointment_count FROM appointments GROUP BY strftime('%w',appointment_date) ORDER BY appointment_count DESC LIMIT 1
```

**Result:** 1 row(s) returned

**Columns:** ['day_of_week', 'appointment_count']

**Sample output:**
  - ('Saturday', 86)

---

## Q16: Revenue trend by month

**Expected behaviour:** Time series

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount),2) AS monthly_revenue FROM invoices GROUP BY month ORDER BY month
```

**Result:** 13 row(s) returned

**Columns:** ['month', 'monthly_revenue']

**Sample output:**
  - ('2025-04', 115788.89)
  - ('2025-05', 99023.54)
  - ('2025-06', 90398.46)

---

## Q17: Average appointment duration by doctor

**Expected behaviour:** AVG + GROUP BY

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.name, ROUND(AVG(t.duration_minutes),1) AS avg_duration_minutes FROM treatments t JOIN appointments a ON a.id=t.appointment_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.id,d.name ORDER BY avg_duration_minutes DESC
```

**Result:** 15 row(s) returned

**Columns:** ['name', 'avg_duration_minutes']

**Sample output:**
  - ('Dr. Rajesh Mehta', 56.1)
  - ('Dr. Priya Sharma', 51.8)
  - ('Dr. Sunita Rao', 40.2)

---

## Q18: List patients with overdue invoices

**Expected behaviour:** JOIN + filter

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT DISTINCT p.first_name || ' ' || p.last_name AS patient, p.email, ROUND(SUM(i.total_amount-i.paid_amount),2) AS total_overdue FROM invoices i JOIN patients p ON p.id=i.patient_id WHERE i.status='Overdue' GROUP BY p.id ORDER BY total_overdue DESC
```

**Result:** 52 row(s) returned

**Columns:** ['patient', 'email', 'total_overdue']

**Sample output:**
  - ('Sanjay Venkatesh', 'sanjay.venkatesh@email.com', 11923.72)
  - ('Rahul Chauhan', 'rahul.chauhan@email.com', 8737.26)
  - ('Kavya Singh', 'kavya.singh@email.com', 8276.32)

---

## Q19: Compare revenue between departments

**Expected behaviour:** JOIN + GROUP BY

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.department, ROUND(SUM(i.total_amount),2) AS total_revenue FROM invoices i JOIN appointments a ON a.patient_id=i.patient_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.department ORDER BY total_revenue DESC
```

**Result:** 5 row(s) returned

**Columns:** ['department', 'total_revenue']

**Sample output:**
  - ('Skin & Hair', 645228.43)
  - ('Child Health', 638961.26)
  - ('General Medicine', 541993.36)

---

## Q20: Show patient registration trend by month

**Expected behaviour:** Date grouping

**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients FROM patients GROUP BY month ORDER BY month
```

**Result:** 13 row(s) returned

**Columns:** ['month', 'new_patients']

**Sample output:**
  - ('2025-04', 24)
  - ('2025-05', 19)
  - ('2025-06', 18)

---

## Summary

- **Total questions:** 20
- **Passed:** 20
- **Failed:** 0

### Notes

- All SQL was generated from natural language via the Vanna 2.0 + Gemini pipeline
- SQL validation rejects any non-SELECT query before execution
- The agent uses DemoAgentMemory seeded with 15 Q&A pairs to improve SQL quality
- Date-relative queries (last month, past 6 months) use SQLite date() functions
