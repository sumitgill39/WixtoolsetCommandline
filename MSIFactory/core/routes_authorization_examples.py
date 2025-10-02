"""
Example of how to update routes with new authorization system
These examples show how to replace the old admin-only checks with new role-based permissions
"""

# Import the new authorization decorators
from core.authorization import (
    require_permission,
    require_admin,
    require_admin_or_poweruser,
    can_user_access,
    get_current_user_role
)

# OLD WAY (Admin only):
"""
@app.route('/add-component', methods=['GET', 'POST'])
def add_component():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
"""

# NEW WAY (Admin or PowerUser):
@app.route('/add-component', methods=['GET', 'POST'])
@require_permission('components', 'create')
def add_component():
    # Route logic here - user permissions already checked by decorator
    pass

# Alternative using the role-based decorator:
@app.route('/add-component', methods=['GET', 'POST'])
@require_admin_or_poweruser()
def add_component_alternative():
    # Route logic here
    pass

# Examples for different component operations:

@app.route('/edit-component/<int:component_id>', methods=['GET', 'POST'])
@require_permission('components', 'update')
def edit_component(component_id):
    # PowerUsers and Admins can edit components
    pass

@app.route('/delete-component/<int:component_id>', methods=['POST'])
@require_permission('components', 'delete')
def delete_component(component_id):
    # PowerUsers and Admins can delete components
    pass

@app.route('/toggle-component/<int:component_id>', methods=['POST'])
@require_permission('components', 'enable_disable')
def toggle_component(component_id):
    # PowerUsers and Admins can enable/disable components
    pass

# Admin-only routes (like user management):
@app.route('/manage-users')
@require_admin()
def manage_users():
    # Only admins can manage users
    pass

@app.route('/system-settings')
@require_permission('system', 'update')
def system_settings():
    # Only admins have system permissions
    pass

# Template context helper - add user permissions to template context
@app.context_processor
def inject_user_permissions():
    """Inject user permissions into all templates"""
    if 'username' in session:
        return {
            'user_role': get_current_user_role(),
            'can_create_components': can_user_access('components', 'create'),
            'can_edit_components': can_user_access('components', 'update'),
            'can_delete_components': can_user_access('components', 'delete'),
            'can_manage_users': can_user_access('users', 'create'),
            'is_admin': get_current_user_role() == 'admin',
            'is_poweruser': get_current_user_role() in ['admin', 'poweruser']
        }
    return {
        'user_role': None,
        'can_create_components': False,
        'can_edit_components': False,
        'can_delete_components': False,
        'can_manage_users': False,
        'is_admin': False,
        'is_poweruser': False
    }

# Component Configuration route example:
@app.route('/component-configuration')
@require_permission('components', 'read')  # All roles can view
def component_configuration():
    # Get components based on user permissions
    username = session.get('username')
    user_role = get_current_user_role()

    # All users can see components, but actions depend on permissions
    components = get_all_components_from_database()

    return render_template('component_configuration.html',
                         components=components,
                         user_permissions={
                             'can_create': can_user_access('components', 'create'),
                             'can_edit': can_user_access('components', 'update'),
                             'can_delete': can_user_access('components', 'delete'),
                             'can_toggle': can_user_access('components', 'enable_disable')
                         })

"""
Template usage examples:

In component_configuration.html:
{% if can_create_components %}
    <a href="{{ url_for('add_component') }}" class="btn btn-primary">
        <i class="fas fa-plus"></i> Add Component
    </a>
{% endif %}

{% if can_edit_components %}
    <a href="{{ url_for('edit_component', component_id=component.id) }}" class="btn btn-warning">
        <i class="fas fa-edit"></i> Edit
    </a>
{% endif %}

{% if can_delete_components %}
    <button onclick="deleteComponent({{ component.id }})" class="btn btn-danger">
        <i class="fas fa-trash"></i> Delete
    </button>
{% endif %}

Role-based navigation:
{% if is_admin %}
    <li><a href="{{ url_for('manage_users') }}">User Management</a></li>
{% endif %}

{% if is_poweruser %}
    <li><a href="{{ url_for('component_configuration') }}">Manage Components</a></li>
{% endif %}
"""