
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB_NAME = "placement_tracker.db"

st.set_page_config(
    page_title="Placement Tracker",
    page_icon="🎯",
    layout="wide"
)


# ---------- DATABASE ----------

def connect():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                application_date TEXT NOT NULL,
                status TEXT NOT NULL,
                deadline TEXT,
                notes TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS prep_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT,
                completed INTEGER DEFAULT 0
            )
        """)


def read_data(table):
    with connect() as conn:
        return pd.read_sql_query(
            f"SELECT * FROM {table} ORDER BY id DESC",
            conn
        )


initialize_database()


# ---------- PAGE DESIGN ----------

st.title("🎯 Placement Preparation Tracker")
st.caption("Organize job applications, preparation tasks and placement progress.")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Job Applications", "Preparation Tasks"]
)


# ---------- DASHBOARD ----------

if page == "Dashboard":

    applications = read_data("applications")
    tasks = read_data("prep_tasks")

    total_jobs = len(applications)
    total_tasks = len(tasks)

    completed_tasks = (
        int(tasks["completed"].sum()) if total_tasks else 0
    )

    pending_tasks = total_tasks - completed_tasks

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Applications", total_jobs)
    col2.metric("Preparation Tasks", total_tasks)
    col3.metric("Completed Tasks", completed_tasks)
    col4.metric("Pending Tasks", pending_tasks)

    st.subheader("Recent Job Applications")

    if applications.empty:
        st.info("No applications added yet. Go to Job Applications to add one.")
    else:
        st.dataframe(applications, use_container_width=True)

    st.subheader("Preparation Progress")

    if total_tasks:
        progress = completed_tasks / total_tasks
        st.progress(progress)
        st.write(f"{progress * 100:.1f}% completed")
    else:
        st.info("Add preparation tasks to track your progress.")


# ---------- JOB APPLICATIONS ----------

elif page == "Job Applications":

    st.header("Manage Job Applications")

    with st.form("application_form"):

        company = st.text_input("Company Name")
        role = st.text_input("Job Role")

        application_date = st.date_input(
            "Application Date",
            value=date.today()
        )

        status = st.selectbox(
            "Application Status",
            [
                "Applied",
                "Assessment",
                "Interview",
                "Selected",
                "Rejected"
            ]
        )

        deadline = st.date_input(
            "Next Deadline",
            value=None
        )

        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add Application")

        if submitted:
            if not company.strip() or not role.strip():
                st.error("Please enter both company name and job role.")
            else:
                with connect() as conn:
                    conn.execute("""
                        INSERT INTO applications
                        (company, role, application_date, status, deadline, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        company.strip(),
                        role.strip(),
                        application_date.isoformat(),
                        status,
                        deadline.isoformat() if deadline else None,
                        notes.strip()
                    ))

                st.success("Application added successfully!")
                st.rerun()

    st.subheader("Your Applications")
    st.subheader("Upcoming Deadlines")

    all_applications = read_data("applications")

    if not all_applications.empty:
        all_applications["deadline"] = pd.to_datetime(
            all_applications["deadline"],
            errors="coerce"
        )

        today = pd.Timestamp(date.today())

        upcoming = all_applications[
            (all_applications["deadline"] >= today) &
            (all_applications["deadline"] <= today + pd.Timedelta(days=7))
        ]

        if not upcoming.empty:
            st.warning("You have application deadlines within the next 7 days.")
            st.dataframe(
                upcoming[["company", "role", "deadline", "status"]],
                use_container_width=True
            )
        else:
            st.success("No upcoming deadlines within 7 days.")
    else:
        st.info("Add applications with deadlines to see alerts.")

    applications = read_data("applications")

    if not applications.empty:
        search = st.text_input("Search by company name")

        status_filter = st.selectbox(
            "Filter by application status",
            ["All", "Applied", "Assessment", "Interview", "Selected", "Rejected"]
        )

        if search:
            applications = applications[
                applications["company"].str.contains(
                    search, case=False, na=False
                )
            ]

        if status_filter != "All":
            applications = applications[
                applications["status"] == status_filter
            ]

        if not applications.empty:
            st.dataframe(applications, use_container_width=True)

            selected_id = st.selectbox(
                "Select application ID to update or delete",
                applications["id"].tolist()
            )

            selected_status = st.selectbox(
                "Update status",
                ["Applied", "Assessment", "Interview", "Selected", "Rejected"]
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Update Status"):
                    with connect() as conn:
                        conn.execute(
                            "UPDATE applications SET status=? WHERE id=?",
                            (selected_status, selected_id)
                        )
                    st.success("Status updated.")
                    st.rerun()

            with col2:
                if st.button("Delete Application"):
                    with connect() as conn:
                        conn.execute(
                            "DELETE FROM applications WHERE id=?",
                            (selected_id,)
                        )
                    st.success("Application deleted.")
                    st.rerun()

            csv = applications.to_csv(index=False).encode("utf-8")

            st.download_button(
                "Download Applications as CSV",
                data=csv,
                file_name="job_applications.csv",
                mime="text/csv"
            )
        else:
            st.info("Your application list is empty.")


# ---------- PREPARATION TASKS ----------

elif page == "Preparation Tasks":
    st.success("Preparation Tasks page is loading!")

    st.header("Manage Preparation Tasks")

    with st.form("task_form"):

        task = st.text_input("Task Name")

        category = st.selectbox(
            "Category",
            ["DSA", "Python", "C++", "Aptitude", "Core Subjects", "Projects", "Interview"]
        )

        priority = st.selectbox(
            "Priority",
            ["High", "Medium", "Low"]
        )

        due_date = st.date_input("Due Date", value=None)

        submitted = st.form_submit_button("Add Task")

        if submitted:
            if not task.strip():
                st.error("Please enter a task name.")
            else:
                with connect() as conn:
                    conn.execute("""
                        INSERT INTO prep_tasks
                        (task, category, priority, due_date)
                        VALUES (?, ?, ?, ?)
                    """, (
                        task.strip(),
                        category,
                        priority,
                        due_date.isoformat() if due_date else None
                    ))

                st.success("Task added successfully!")
                st.rerun()

    st.subheader("Your Preparation Tasks")

    tasks = read_data("prep_tasks")

    if not tasks.empty:

        for _, row in tasks.iterrows():
            is_completed = bool(row["completed"])

            label = f"{row['task']} | {row['category']} | {row['priority']}"

            checked = st.checkbox(
                label,
                value=is_completed,
                key=f"task_{row['id']}"
            )

            if checked != is_completed:
                with connect() as conn:
                    conn.execute(
                        "UPDATE prep_tasks SET completed=? WHERE id=?",
                        (int(checked), int(row["id"]))
                    )
                st.rerun()

        st.dataframe(tasks, use_container_width=True)

        task_id = st.selectbox(
            "Select task ID to delete",
            tasks["id"].tolist()
        )

        if st.button("Delete Task"):
            with connect() as conn:
                conn.execute(
                    "DELETE FROM prep_tasks WHERE id=?",
                    (task_id,)
                )
            st.success("Task deleted.")
            st.rerun()

    else:
        st.info("No preparation tasks added yet.")
