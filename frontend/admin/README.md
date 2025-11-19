# Admin Frontend - User Management

This document describes the admin frontend implementation for the FHIR System.

## Overview

The admin frontend provides a web interface for administrators to manage users in the system. It includes capabilities to create, read, update, delete users, and assign roles.

## Directory Structure

```
frontend/admin/
├── templates/
│   ├── admin_dashboard.html   # Main dashboard
│   ├── users_list.html        # User list with search/filter
│   ├── user_create.html       # Create new user form
│   └── user_edit.html         # Edit existing user form
└── static/
    ├── css/
    │   └── admin.css          # Custom styles
    └── js/
        ├── admin-dashboard.js # Dashboard functionality
        ├── admin-users.js     # User list management
        ├── admin-user-form.js # User creation logic
        └── admin-user-edit.js # User editing logic
```

## Pages and Features

### 1. Admin Dashboard (`/admin` or `/admin/dashboard`)

**Features:**
- System statistics display:
  - Total active users
  - Total patients
  - Total practitioners (doctors)
  - Total administrators
- Quick action buttons:
  - Create new user
  - View users list
- System status indicators
- Auto-refresh statistics every 30 seconds

**JavaScript:** `admin-dashboard.js`
- Token synchronization from cookie to localStorage
- Loads user statistics from `/api/admin/users`
- Calculates stats by user type
- Animates counter updates

### 2. User Management Page (`/admin/users`)

**Features:**
- List all users with pagination (10 per page)
- Search functionality (username, email, full name)
- Filter by role (admin, practitioner, patient, auditor, admission)
- Per-user actions:
  - Edit user details
  - Assign/change role
  - Delete user (with confirmation)
- Role assignment modal for quick changes

**JavaScript:** `admin-users.js`
- Fetches users from `/api/admin/users`
- Client-side filtering and pagination
- Delete confirmation with modal
- Role assignment with modal
- Success/error notifications

### 3. Create User Page (`/admin/users/new`)

**Features:**
- Form fields:
  - Username (required, min 3 chars)
  - Email (required, valid email)
  - Full name (required)
  - Password (required, min 6 chars)
  - Confirm password (must match)
  - User role (required)
  - Superuser flag (optional)
- Client-side validation
- Password visibility toggle
- Success redirect to users list

**JavaScript:** `admin-user-form.js`
- Form validation
- Password matching check
- POST to `/api/admin/users`
- Success/error handling

### 4. Edit User Page (`/admin/users/{user_id}/edit`)

**Features:**
- Load existing user data
- Editable fields:
  - Email
  - Full name
  - Password (optional)
  - User role
  - Superuser flag
- Username is read-only (cannot be changed)
- Partial updates (only changed fields sent)
- Success redirect to users list

**JavaScript:** `admin-user-edit.js`
- Fetches user data from `/api/admin/users/{user_id}`
- Populates form with existing data
- PATCH to `/api/admin/users/{user_id}`
- Success/error handling

## Backend Integration

### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/users` | List all users |
| POST | `/api/admin/users` | Create new user |
| GET | `/api/admin/users/{user_id}` | Get user details |
| PATCH | `/api/admin/users/{user_id}` | Update user |
| DELETE | `/api/admin/users/{user_id}` | Delete user |
| POST | `/api/admin/users/{user_id}/role` | Assign role |

### Authentication

All API calls require authentication with an admin role. The frontend uses JWT tokens stored in:
1. `localStorage.authToken` (primary)
2. Cookie `authToken` (fallback)

The token is automatically synchronized from cookie to localStorage on page load.

### Request Headers

```javascript
{
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

## User Roles

The system supports the following roles:

- **admin**: Full administrative access
- **practitioner**: Medical staff (doctors)
- **patient**: System patients
- **auditor**: Audit and monitoring access
- **admission**: Admission staff

## Styling

The admin frontend uses:
- Bootstrap 5.3.2 for layout and components
- Bootstrap Icons for iconography
- Custom CSS (`admin.css`) for branding and enhancements

### Design Principles

1. **Consistency**: Follows the same design patterns as other frontend layers
2. **Responsiveness**: Mobile-friendly design
3. **Accessibility**: Proper semantic HTML and ARIA labels
4. **User Experience**: Clear feedback, loading states, and error messages

## Security Considerations

1. **Authentication**: All pages check for valid JWT token
2. **Authorization**: Backend enforces admin role requirements
3. **Input Validation**: Both client-side and server-side validation
4. **XSS Prevention**: HTML escaping in JavaScript
5. **CSRF**: Not applicable (API uses JWT, not session cookies)

## Error Handling

The frontend provides user-friendly error messages for:
- Network errors
- Authentication failures (401/403)
- Validation errors
- Server errors (500)

All errors are displayed as Bootstrap alerts with appropriate icons and colors.

## Testing

### Manual Testing Checklist

- [ ] Dashboard loads and displays statistics
- [ ] Users list displays all users
- [ ] Search functionality works
- [ ] Filter by role works
- [ ] Pagination works correctly
- [ ] Create user form validates inputs
- [ ] Create user succeeds and redirects
- [ ] Edit user loads existing data
- [ ] Edit user saves changes
- [ ] Role assignment modal works
- [ ] Delete user confirmation works
- [ ] Delete user removes user from list
- [ ] All error cases show appropriate messages
- [ ] Logout works correctly

### Browser Compatibility

Tested and compatible with:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Future Enhancements

Possible improvements for future versions:

1. **Bulk Operations**: Select multiple users for batch actions
2. **Export**: Export user list to CSV/Excel
3. **Advanced Filters**: More filtering options (status, created date, etc.)
4. **User Activity**: Show last login and activity
5. **Password Reset**: Admin can send password reset emails
6. **User Groups**: Organize users into groups
7. **Audit Log**: View user management history

## Troubleshooting

### Users Not Loading

1. Check browser console for errors
2. Verify JWT token is present in localStorage
3. Verify backend `/api/admin/users` endpoint is accessible
4. Check that user has admin role

### Authentication Issues

1. Clear localStorage and cookies
2. Login again
3. Verify token format (should be JWT)
4. Check token expiration

### Styling Issues

1. Verify `/admin/static/` files are being served
2. Check browser network tab for 404s on CSS/JS files
3. Clear browser cache

## Support

For issues or questions, please refer to:
- Backend API documentation: `doc/admin_backend.md`
- Main README: `README.md`
- Issue tracker: GitHub Issues
