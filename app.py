import yaml
import requests
from datetime import datetime
import csv

completed_tasks = []


# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

api_key = config["clickup"]["api_key"]
folder_id = config["clickup"]["folder_id"]

headers = {
    "Authorization": api_key
}

# Step 1: Get all lists in the folder
lists_url = f"https://api.clickup.com/api/v2/folder/{folder_id}/list"
lists_resp = requests.get(lists_url, headers=headers)
lists_resp.raise_for_status()
lists_data = lists_resp.json()

if not lists_data.get("lists"):
    print("No lists found in this folder.")
    exit()

tasks_found = False

## find details of tasks in each list
def get_task_details(task_id):
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers = {"Authorization": api_key}
    params = {"include_subtasks": "true"}
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()

    # Subtask count
    subtask_count = len(data.get("subtasks", []))

    # Helper to extract relationships from any source
    def extract_relationships(source_list):
        relationships = []
        EXCLUDED_NAMES = {"Arifin", "Geta Kinanti", "Malik Alamsyah"}
        for link in source_list:
            rel_task_id = link.get("task_id")
            rel_type = link.get("type")  # numeric relationship type
            if rel_task_id:
                rel_task_data = get_task_info(rel_task_id)
                relationships.append({
                    "type": rel_type,
                    "task_id": rel_task_id,
                    "task_name": rel_task_data.get("name"),
                    "assignees": [
                        a.get("username") 
                        for a in rel_task_data.get("assignees", [])
                        if a.get("username") not in EXCLUDED_NAMES
                    ]
                })
        return relationships

    # Try linked_tasks first
    relationships = extract_relationships(data.get("linked_tasks", []))

    # If no linked_tasks, try dependencies
    if not relationships:
        relationships = extract_relationships(data.get("dependencies", []))

    return {
        "subtask_count": subtask_count,
        "relationships": relationships
    }


def get_task_info(task_id):
    """Get minimal info about a task (name + assignees)."""
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers = {"Authorization": api_key}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {}

## find subtasks in each list
def get_subtask_count(task_id):
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers = {"Authorization": api_key}
    params = {"include_subtasks": "true"}
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    print(data)
    return len(data.get("subtasks", []))

# Step 2: Loop through each list and get completed tasks
for lst in lists_data["lists"]:
    list_id = lst["id"]
    tasks_url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    params = {
        "archived": "false",
        "include_closed": "true"  # Ensure completed tasks are included
    }
    tasks_resp = requests.get(tasks_url, headers=headers, params=params)
    tasks_resp.raise_for_status()
    tasks_data = tasks_resp.json()

    for task in tasks_data.get("tasks", []):
        if task["status"]["type"] == "closed":
            tasks_found = True
            task_id = task["id"]
            closed_ts = task.get("date_closed")
            if closed_ts:
                closed_date = datetime.fromtimestamp(int(closed_ts) / 1000).strftime("%d-%m-%Y")
            else:
                closed_date = "-"
            task_details = get_task_details(task_id)
            subtasks_count = task_details["subtask_count"]
            # Extract task name, subtask count, and relationships
            if task_details["relationships"]:
                task_name = task_details["relationships"][0]["task_name"]
                task_assignees = task_details["relationships"][0]["assignees"]
            else:
                task_name = task["name"]
                task_assignees = "No Linked Tasks"

            completed_tasks.append([task_name, subtasks_count, closed_date, task_assignees])

            # print(f"{task_name} | {subtasks_count} | {closed_date} | {task_assignees}")

# Save to CSV
with open("completed_tasks.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Task Name", "Subtask Count", "Closed Date", "Assignees"])
    writer.writerows(completed_tasks)

print("✅ Data saved to completed_tasks.csv")

if not tasks_found:
    print("No completed tasks found.")
