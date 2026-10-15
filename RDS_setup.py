# import psycopg2, os
# from dotenv import load_dotenv
# load_dotenv()

# conn = psycopg2.connect(
#     host=os.getenv("RDS_HOST"), port=os.getenv("RDS_PORT"),
#     dbname=os.getenv("RDS_DATABASE"), user=os.getenv("RDS_USER"),
#     password=os.getenv("RDS_PASSWORD")
# )
# print("Connected successfully")
# conn.close()


## documentation code blocks
# schema context
# clients table:
# - id (integer, primary key)
# - name (text) — client organization name
# - industry (text) — client's industry sector
# - region (text) — geographic region, one of: 'North', 'South', 'East', 'West'
# - contract_value (numeric) — total contract value in USD
# - created_date (date) — date the client relationship began

# projects table:
# - id (integer, primary key)
# - client_id (integer, foreign key referencing clients.id)
# - name (text) — project name
# - status (text) — project status
# - start_date (date) — project start date
# - end_date (date) — project end date
# - budget (numeric) — project budget

# consultants table:
# - id (integer, primary key)
# - name (text) — consultant name
# - grade (text) — consultant grade
# - specialisation (text) — consultant specialisation
# - project_id (integer, foreign key referencing projects.id)
# - billable_hours (numeric) — billable hours

# invoices table:
# - id (integer, primary key)
# - project_id (integer, foreign key referencing projects.id)
# - amount (numeric) — invoice amount
# - status (text) — invoice status
# - due_date (date) — invoice due date
# - paid_date (date) — invoice paid date

import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("RDS_HOST"), port=os.getenv("RDS_PORT"),
    dbname=os.getenv("RDS_DATABASE"), user=os.getenv("RDS_USER"),
    password=os.getenv("RDS_PASSWORD")
)
cur = conn.cursor()

# cur.execute("""
    
#     CREATE TABLE IF NOT EXISTS clients (
#         id SERIAL PRIMARY KEY,
#         name TEXT NOT NULL,
#         industry TEXT,
#         region TEXT,
#         contract_value NUMERIC,
#         created_date DATE
#     )
# """)

# cur.execute("""
#      DROP TABLE IF EXISTS projects
    
#     CREATE TABLE IF NOT EXISTS projects (
#         id SERIAL PRIMARY KEY,
#         client_id INTEGER REFERENCES clients(id),
#         name TEXT NOT NULL,
#         status TEXT,
#         start_date DATE,
#         end_date DATE,
#         budget NUMERIC
#     )
# """)

# cur.execute("""
#     DROP TABLE IF EXISTS consultants
    
#     CREATE TABLE IF NOT EXISTS consultants (
#         id SERIAL PRIMARY KEY,
#         name TEXT NOT NULL,
#         grade TEXT,
#         specialisation TEXT,
#         project_id INTEGER REFERENCES projects(id),
#         billable_hours NUMERIC
#     )
# """)

# cur.execute("""
#     DROP TABLE IF EXISTS invoices;
    
#     CREATE TABLE IF NOT EXISTS invoices (
#         id SERIAL PRIMARY KEY,
#         project_id INTEGER REFERENCES projects(id),
#         amount NUMERIC,
#         status TEXT,
#         due_date DATE,
#         paid_date DATE
#     )
# """)

# conn.commit()
# print("Tables created successfully")

# cur.execute("DELETE FROM consultants;")
# cur.execute("DELETE FROM invoices;")
# cur.execute("DELETE FROM projects;")
# cur.execute("DELETE FROM clients;")



# cur.execute("""
#     INSERT INTO clients (name, industry, region, contract_value, created_date)
#     VALUES
#         ('Acme Corp', 'Retail', 'North', 250000, '2025-01-15'),
#         ('Beta Financial', 'Finance', 'East', 480000, '2025-03-01'),
#         ('Charlie Industries', 'Manufacturing', 'South', 320000, '2025-02-20'),
#         ('Delta Tech', 'Technology', 'West', 600000, '2025-04-10'),
#         ('Epsilon Solutions', 'Healthcare', 'Central', 420000, '2025-05-01')
# """)

# cur.execute("""
#     INSERT INTO projects (client_id, name, status, start_date, end_date, budget)
#     VALUES
#         (1, 'Project Alpha', 'Completed', '2025-01-15', '2025-06-15', 250000),
#         (2, 'Project Beta', 'Active', '2025-03-01', '2025-08-01', 480000),
#         (3, 'Project Charlie', 'On-Hold', '2025-02-20', '2025-07-20', 320000),
#         (4, 'Project Delta', 'Active', '2025-04-10', '2025-09-10', 600000),
#         (5, 'Project Epsilon', 'Completed', '2025-05-01', '2025-10-01', 420000)
# """)

# cur.execute("""
#     INSERT INTO consultants (name, grade, specialisation, project_id, billable_hours)
#     VALUES
#         ('John Brown', 'Senior', 'Software Engineer', 1, 160),
#         ('Erica Smith', 'Mid-level', 'Data Analyst', 2, 120),
#         ('Bob Williams', 'Junior', 'Sales Associate', 3, 80),
#         ('Alice Franklin', 'Senior', 'Project Manager', 4, 180),
#         ('Charles Davis', 'Mid-level', 'Marketing Specialist', 5, 100) 
# """)

# cur.execute("""
#     INSERT INTO invoices (project_id, amount, status, due_date, paid_date)
#     VALUES
#         (1, 250000, 'Paid', '2025-06-15', '2025-06-14'),
#         (2, 480000, 'Pending', '2025-08-01', NULL),
#         (3, 320000, 'Overdue', '2025-07-20', NULL),
#         (4, 600000, 'Pending', '2025-09-10', NULL),
#         (5, 420000, 'Paid', '2025-10-01', '2025-09-25')
# """)

# conn.commit()


# try:
#     cur.execute("""
#         TRUNCATE TABLE
#             consultants,
#             invoices,
#             projects,
#             clients
#         RESTART IDENTITY CASCADE;
#     """)

#     cur.execute("""
#         INSERT INTO clients (name, industry, region, contract_value, created_date)
#         VALUES
#             ('Acme Corp', 'Retail', 'North', 250000, '2025-01-15'),
#             ('Beta Financial', 'Finance', 'East', 480000, '2025-03-01'),
#             ('Charlie Industries', 'Manufacturing', 'South', 320000, '2025-02-20'),
#             ('Delta Tech', 'Technology', 'West', 600000, '2025-04-10'),
#             ('Epsilon Solutions', 'Healthcare', 'Central', 420000, '2025-05-01')
#     """)

#     cur.execute("""
#         INSERT INTO projects
#             (client_id, name, status, start_date, end_date, budget)
#         VALUES
#             (1, 'Project Alpha', 'Completed', '2025-01-15', '2025-06-15', 250000),
#             (2, 'Project Beta', 'Active', '2025-03-01', '2025-08-01', 480000),
#             (3, 'Project Charlie', 'On-Hold', '2025-02-20', '2025-07-20', 320000),
#             (4, 'Project Delta', 'Active', '2025-04-10', '2025-09-10', 600000),
#             (5, 'Project Epsilon', 'Completed', '2025-05-01', '2025-10-01', 420000)
#     """)

#     cur.execute("""
#         INSERT INTO consultants
#             (name, grade, specialisation, project_id, billable_hours)
#         VALUES
#             ('John Brown', 'Senior', 'Software Engineer', 1, 160),
#             ('Erica Smith', 'Mid-level', 'Data Analyst', 2, 120),
#             ('Bob Williams', 'Junior', 'Sales Associate', 3, 80),
#             ('Alice Franklin', 'Senior', 'Project Manager', 4, 180),
#             ('Charles Davis', 'Mid-level', 'Marketing Specialist', 5, 100)
#     """)

#     cur.execute("""
#         INSERT INTO invoices
#             (project_id, amount, status, due_date, paid_date)
#         VALUES
#             (1, 250000, 'Paid', '2025-06-15', '2025-06-14'),
#             (2, 480000, 'Pending', '2025-08-01', NULL),
#             (3, 320000, 'Overdue', '2025-07-20', NULL),
#             (4, 600000, 'Pending', '2025-09-10', NULL),
#             (5, 420000, 'Paid', '2025-10-01', '2025-09-25')
#     """)

#     conn.commit()

# except Exception:
#     conn.rollback()
#     raise
#Continue for projects, consultants, invoices — make sure foreign keys reference real IDs

cur.execute("""
    SELECT c.name AS client, p.name AS project, con.name AS consultant, i.amount
    FROM clients c
    JOIN projects p ON p.client_id = c.id
    JOIN consultants con ON con.project_id = p.id
    JOIN invoices i ON i.project_id = p.id
""")


rows = cur.fetchall()

for row in rows:
    print(row)
