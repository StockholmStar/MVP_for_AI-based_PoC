from app.services import storage
from app.workflow.product_graph import DEMO_IDEA, run_product_workflow


def main() -> None:
    storage.init_db()
    project = None
    for item in storage.list_projects():
        if item["name"] == "Smart Notification Summary":
            project = item
            break
    if not project:
        project = storage.create_project("Smart Notification Summary", "Built-in phone system software demo case.", DEMO_IDEA)
    if not storage.list_artefacts(project["id"]):
        state = run_product_workflow(project["id"], DEMO_IDEA)
        storage.save_run_and_artefacts(project["id"], DEMO_IDEA, dict(state))
    print(f"Demo project ready: {project['id']}")


if __name__ == "__main__":
    main()
