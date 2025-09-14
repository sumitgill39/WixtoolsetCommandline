# MSI Factory Authentication System

Simple authentication system with user login, access requests, and admin approval workflow.

## 🚀 Quick Start

### 1. Install Requirements
```bash
pip install flask
```

### 2. Run the Authentication System
```bash
cd auth
python simple_auth.py
```

### 3. Open in Browser
```
http://localhost:5000
```

## 👥 Demo Accounts

### Admin Account
- **Username**: `admin`
- **Role**: Administrator
- **Access**: Can approve/deny requests and access admin panel

### Regular User
- **Username**: `john.doe`
- **Role**: Regular user
- **Access**: Can access approved applications

### New User
- **Username**: Any other username (e.g., `jane.smith`)
- **Flow**: Will be redirected to access request form

## 🔄 How It Works

### 1. **User Login** 
- User enters username and domain
- System checks if user exists and is approved

### 2. **Access Request** (New Users)
- Fill personal information form
- Select application from dropdown (AppShortKey verification)
- Provide reason for access
- Request submitted to admin

### 3. **Admin Approval**
- Admin sees pending requests in admin panel
- Can approve or deny each request
- Approved users can login and access their applications

### 4. **User Dashboard**
- Shows user profile and applications
- Lists approved applications
- Provides quick actions for MSI generation (coming soon)

## 📁 File Structure

```
auth/
├── simple_auth.py           # Main Flask application
├── templates/               # HTML templates
│   ├── base.html           # Base template with styling
│   ├── login.html          # Login page
│   ├── access_request.html # Access request form
│   ├── dashboard.html      # User dashboard
│   └── admin.html          # Admin panel
├── database/               # JSON database files (auto-created)
│   ├── users.json          # User accounts
│   ├── access_requests.json # Access requests
│   └── applications.json   # Available applications
└── README.md               # This file
```

## 💾 Database

The system uses simple JSON files for data storage:

### Users Database (`users.json`)
```json
{
  "users": [
    {
      "username": "john.doe",
      "email": "john.doe@company.com",
      "first_name": "John",
      "last_name": "Doe",
      "status": "approved",
      "role": "user",
      "approved_apps": ["WEBAPP01", "PORTAL"]
    }
  ]
}
```

### Applications Database (`applications.json`)
```json
{
  "applications": [
    {
      "app_short_key": "WEBAPP01",
      "app_name": "Customer Portal Web App",
      "description": "Customer-facing web portal",
      "owner_team": "Customer Experience",
      "status": "active"
    }
  ]
}
```

## 🎯 Features

### ✅ Implemented
- **User Login** - Domain-based authentication
- **Access Request Form** - New user registration
- **AppShortKey Validation** - Verify against application registry
- **Admin Approval System** - Approve/deny access requests
- **User Dashboard** - Profile and application access
- **Admin Panel** - Manage pending requests
- **Role-based Access** - Admin vs regular user permissions

### 🔄 Coming Soon
- **Domain Integration** - Active Directory authentication
- **Email Notifications** - Request status notifications
- **User Management** - Edit user details and permissions
- **Application Management** - Add/edit applications
- **Audit Logging** - Track all user actions
- **API Integration** - ServiceNow server validation

## 🛠️ Customization

### Add New Applications
1. Edit `database/applications.json`
2. Add new application object:
```json
{
  "app_short_key": "NEWAPP",
  "app_name": "New Application",
  "description": "Description here",
  "owner_team": "Your Team",
  "status": "active"
}
```

### Change Styling
- Edit `templates/base.html` CSS section
- Modify color scheme in the `<style>` section

### Add New User Roles
- Edit `simple_auth.py`
- Modify role checking logic in routes
- Update templates to show role-specific content

## 🔒 Security Notes

### Current Implementation (Development)
- Simple JSON file storage
- No password validation
- Basic session management

### Production Recommendations
- Use proper database (PostgreSQL, MySQL)
- Implement password hashing
- Add HTTPS/TLS
- Use secure session configuration
- Add CSRF protection
- Implement rate limiting
- Add input validation and sanitization

## 🧪 Testing

### Test User Login
1. Go to login page
2. Enter `admin` or `john.doe`
3. Should redirect to dashboard

### Test Access Request
1. Go to login page
2. Enter any new username (e.g., `test.user`)
3. Fill access request form
4. Login as `admin` to approve
5. Login with new user to access dashboard

### Test Admin Functions
1. Login as `admin`
2. Go to Admin Panel
3. View pending requests
4. Approve/deny requests

## 🚀 Next Steps

1. **Test the Authentication System**
2. **Connect to MSI Factory Core Engine**
3. **Add Domain Integration**
4. **Implement Real Database**
5. **Add Email Notifications**

---

**Ready to test!** Run the system and try the different user flows to see how authentication, access requests, and admin approval work together.