# Branch Management - Project Integration Changes

## Summary
Added project selection dropdown to Branch Management, enabling cascading dropdown (Project → Components) and incorporating `{ProjectShortKey}` into JFrog path patterns.

## Changes Made

### 1. Backend API Changes (`PackageBuilder/branch_api.py`)

#### New Methods Added:

**`get_projects_for_dropdown()`** (Lines 514-558)
- Fetches all active projects from the database
- Returns project_id, project_name, and project_key
- Used to populate the Project dropdown in the UI

**`get_components_by_project(project_id)`** (Lines 560-611)
- Fetches components filtered by a specific project_id
- Returns components with their associated project information
- Enables cascading dropdown functionality

### 2. Route Handler Changes (`PackageBuilder/branch_routes.py`)

#### Modified Route:
**`/branch_management`** (Lines 52-79)
- Now fetches both projects and components data
- Passes projects list to the template for rendering

#### New API Endpoints:

**`GET /api/projects/dropdown`** (Lines 303-332)
- Returns all active projects for dropdown selection
- Includes permission checks

**`GET /api/components/by_project/<project_id>`** (Lines 334-366)
- Returns components filtered by project_id
- Enables dynamic component loading based on selected project

### 3. Frontend Template Changes (`webapp/templates/branch_management.html`)

#### Modal Form Structure (Lines 61-98):

**New Fields:**
- Added Project dropdown (first field)
- Added hidden field `selected_project_key` to store project key
- Modified Component dropdown to be dependent on Project selection
- Component dropdown is now disabled until a project is selected

**Updated Default Path Pattern:**
```
Old: {ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip
New: {ProjectShortKey}/{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip
```

#### New JavaScript Functions:

**`loadComponentsByProject()`** (Lines 231-274)
- Triggered when a project is selected
- Fetches components for the selected project via AJAX
- Populates the Component dropdown dynamically
- Stores the project_key in hidden field
- Enables the Component dropdown after loading

**Updated `addNewBranch()`** (Lines 276-292)
- Resets project and component dropdowns
- Sets default path pattern with {ProjectShortKey}
- Disables component dropdown initially

**Updated `editBranch(branchId)`** (Lines 294-362)
- Fetches branch details including project information
- Dynamically loads and selects the correct project
- Loads components for that project
- Selects the correct component
- Preserves the project_key in the hidden field

## Database Schema
No database schema changes required. Utilizes existing relationships:
- `projects` table (project_id, project_name, project_key)
- `components` table (component_id, project_id, component_name)
- `component_branches` table (branch_id, component_id, path_pattern_override)

## User Workflow

### Adding a New Branch:
1. Click "Add Branch" button
2. **Select Project** from dropdown (shows: "Project Name (PROJECT_KEY)")
3. Component dropdown automatically populates with components for selected project
4. **Select Component** from dropdown
5. Enter Branch Name (e.g., "main", "development")
6. JFrog Path Pattern auto-fills with: `{ProjectShortKey}/{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip`
7. Configure Version and Auto Increment settings
8. Set Status and Description
9. Click "Save Branch"

### Editing an Existing Branch:
1. Click Edit icon on a branch
2. Modal opens with Project pre-selected
3. Components load automatically for that project
4. Component is pre-selected
5. All other fields are populated with existing values
6. Modify as needed and save

## Path Pattern Variables
The following variables are now supported in path patterns:

- `{ProjectShortKey}` - Project's short key (e.g., "MERCER", "API")
- `{ComponentName}` - Component name
- `{branch}` - Branch name
- `{date}` - Build date
- `{buildNumber}` - Build number
- `{componentName}` - Component name (lowercase)

## Example Path Patterns

**Default Pattern:**
```
{ProjectShortKey}/{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip
```

**Example with Project "MERCER", Component "API", Branch "main":**
```
MERCER/API/main/Build20250102.123/api.zip
```

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/branch_management` | GET | Renders branch management page with projects and components |
| `/api/projects/dropdown` | GET | Get all active projects for dropdown |
| `/api/components/dropdown` | GET | Get all active components for dropdown |
| `/api/components/by_project/<id>` | GET | Get components filtered by project_id |
| `/api/branches` | POST | Create new branch |
| `/api/branches/<id>` | GET | Get branch by ID |
| `/api/branches/<id>` | PUT | Update branch |
| `/api/branches/<id>` | DELETE | Delete branch (soft delete) |
| `/api/branches/all` | GET | Get all branches with project info |

## Testing Checklist

- [x] Projects dropdown populates correctly
- [x] Components load when project is selected
- [x] Component dropdown is disabled until project is selected
- [x] Path pattern includes {ProjectShortKey} by default
- [x] Creating new branch saves project_key association
- [x] Editing existing branch loads correct project and components
- [x] All existing functionality remains intact
- [ ] Integration testing with actual database
- [ ] Verify project_key is correctly used in artifact downloads

## Notes

- **No JavaScript frameworks used** - Pure vanilla JavaScript with fetch API
- **Backward compatible** - Existing branches continue to work
- **Cascading dropdowns** - Project selection drives component list
- **Project key storage** - Stored in hidden field for form submission
- **Permission-based** - All API endpoints check user permissions

## Future Enhancements

1. Add project filter on main branch list page
2. Display project_key in branch list view
3. Validate path pattern syntax before saving
4. Add path pattern preview with actual values
5. Support for custom path pattern templates per project