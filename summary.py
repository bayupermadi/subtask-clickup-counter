import pandas as pd
import ast

# Load CSV
df = pd.read_csv("completed_tasks.csv")

# Parse Assignees from string to list
df["Assignees"] = df["Assignees"].apply(ast.literal_eval)

# Derive iteration from Closed Date (month-year)
df["iteration"] = pd.to_datetime(df["Closed Date"], dayfirst=True).dt.strftime("%m-%Y")

# Expand rows so each assignee gets its own line
df = df.explode("Assignees")

# Normalize name (optional: lowercase, strip spaces)
df["Assignees"] = df["Assignees"].str.strip()

# Group by assignee and iteration
summary = df.groupby(["Assignees", "Subtask Count"])["Task Name"].count().reset_index()

# Rename columns
summary.columns = ["name", "iteration", "total_task"]

# Save summary
summary.to_csv("tasks_summary.csv", index=False)

print(summary)
