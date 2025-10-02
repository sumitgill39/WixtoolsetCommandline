"""Test DB connection and verify component data"""
from db_helper import DatabaseHelper

def test_component_query():
    db = DatabaseHelper()
    if db.connect():
        # Test getting all components
        print("\nAll active components:")
        query = """
            SELECT 
                c.component_id,
                c.component_name,
                p.project_name,
                p.project_key
            FROM components c
            INNER JOIN projects p ON c.project_id = p.project_id
            WHERE c.is_enabled = 1
        """
        components = db.execute_query(query)
        if components:
            for comp in components:
                print(f"ID: {comp['component_id']}, Name: {comp['component_name']}, Project: {comp['project_name']}")
        else:
            print("No components found")

        # Test specific component (ID: 27)
        print("\nTesting component ID 27:")
        component = db.get_component_info(27)
        if component:
            print(f"Found component: {component}")
        else:
            print("Component 27 not found")

        db.disconnect()

if __name__ == "__main__":
    test_component_query()