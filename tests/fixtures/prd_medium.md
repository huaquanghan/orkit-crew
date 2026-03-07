---
project_name: dashboard-app
version: 1.0.0
mode: greenfield
scope: mvp
complexity: medium
stack:
  framework: nextjs
  language: typescript
  styling: tailwind
  ui_library: shadcn
  package_manager: pnpm
nextjs:
  router: app
  src_dir: true
output_dir: ./output/dashboard
---

# 1. Overview

A dashboard application for managing projects and tasks with team collaboration features.

# 2. Goals

- Provide project management capabilities
- Enable team collaboration
- Track task progress
- Visualize project metrics

# 3. Features

## Feature 1: User Authentication
**Priority:** P0

### User Story
As a user, I want to sign up and log in securely.

### Description
Email/password authentication with session management.

### Components
- [ ] Login form
- [ ] Signup form
- [ ] Password reset
- [ ] Session handling

### Acceptance Criteria
- [ ] Users can register with email/password
- [ ] Users can log in
- [ ] Sessions persist across page reloads
- [ ] Protected routes require authentication

## Feature 2: Project Dashboard
**Priority:** P0

### User Story
As a user, I want to see an overview of my projects.

### Description
Dashboard showing project cards with status and progress.

### Components
- [ ] Project cards
- [ ] Status badges
- [ ] Progress bars
- [ ] Quick actions

### Acceptance Criteria
- [ ] Display all user projects
- [ ] Show project status (active, completed, archived)
- [ ] Show completion percentage
- [ ] Click to view project details

## Feature 3: Task Management
**Priority:** P1

### User Story
As a user, I want to create and manage tasks within projects.

### Description
CRUD operations for tasks with priority and due dates.

### Components
- [ ] Task list
- [ ] Task creation form
- [ ] Task edit modal
- [ ] Priority indicators
- [ ] Due date picker

### Acceptance Criteria
- [ ] Create tasks with title, description, priority
- [ ] Edit existing tasks
- [ ] Delete tasks
- [ ] Filter by status and priority
- [ ] Sort by due date

## Feature 4: Team Members
**Priority:** P1

### User Story
As a user, I want to invite team members to projects.

### Description
Team management with role-based access.

### Components
- [ ] Member list
- [ ] Invite form
- [ ] Role selector
- [ ] Permission display

### Acceptance Criteria
- [ ] Invite members by email
- [ ] Assign roles (admin, member, viewer)
- [ ] Remove team members
- [ ] Show member activity

# 4. Page Structure

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Landing | Marketing page | No |
| /login | Login | Authentication | No |
| /signup | Signup | Registration | No |
| /dashboard | Dashboard | Main dashboard | Yes |
| /projects | Projects | Project list | Yes |
| /projects/[id] | Project Detail | Single project view | Yes |
| /tasks | Tasks | Task management | Yes |
| /team | Team | Team management | Yes |
| /settings | Settings | User settings | Yes |

# 5. API Requirements

- POST /api/auth/login
- POST /api/auth/signup
- POST /api/auth/logout
- GET /api/projects
- POST /api/projects
- GET /api/projects/[id]
- PUT /api/projects/[id]
- DELETE /api/projects/[id]
- GET /api/tasks
- POST /api/tasks
- PUT /api/tasks/[id]
- DELETE /api/tasks/[id]

# 6. Database Schema

- Users: id, email, name, created_at
- Projects: id, name, description, owner_id, status, created_at
- Tasks: id, title, description, project_id, assignee_id, priority, status, due_date
- ProjectMembers: id, project_id, user_id, role

# 7. Authentication

- JWT-based authentication
- HttpOnly cookies
- CSRF protection
- Session expiration: 7 days

# 8. UI/UX Guidelines

- Sidebar navigation
- Card-based layouts
- Consistent spacing (4px grid)
- Primary: indigo-600
- Success: green-500
- Warning: yellow-500
- Error: red-500

# 9. Performance

- Route-level code splitting
- Image optimization
- Data caching with React Query
- Optimistic updates

# 10. Security

- Input validation
- XSS protection
- CSRF tokens
- Rate limiting

# 11. Deployment

- Vercel deployment
- Environment variables for API URL
- Analytics integration

# 12. Timeline

Week 1: Auth + Dashboard
Week 2: Tasks + Team
