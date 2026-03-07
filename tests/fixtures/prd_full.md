---
project_name: enterprise-crm
version: 2.0.0
mode: greenfield
scope: full
complexity: high
stack:
  framework: nextjs
  language: typescript
  styling: tailwind
  ui_library: shadcn
  package_manager: pnpm
nextjs:
  router: app
  src_dir: true
output_dir: ./output/crm
---

# 1. Overview

A comprehensive CRM system for enterprise sales teams with lead management,
pipeline tracking, reporting, and team collaboration features.

# 2. Goals

- Centralize customer data
- Streamline sales pipeline
- Automate follow-ups
- Provide actionable insights
- Enable team collaboration
- Integrate with external tools

# 3. Features

## Feature 1: Multi-tenant Authentication
**Priority:** P0

### User Story
As an enterprise user, I want SSO and role-based access.

### Description
Enterprise authentication with SAML, OAuth, and MFA support.

### Components
- [ ] SSO integration
- [ ] MFA setup
- [ ] Role management
- [ ] Permission system
- [ ] Organization switching

### Acceptance Criteria
- [ ] SAML 2.0 support
- [ ] Google/Microsoft OAuth
- [ ] TOTP-based MFA
- [ ] Granular permissions
- [ ] Organization isolation

## Feature 2: Contact Management
**Priority:** P0

### User Story
As a sales rep, I want to manage contacts and companies.

### Description
Full CRM contact management with custom fields and history.

### Components
- [ ] Contact profiles
- [ ] Company profiles
- [ ] Custom fields
- [ ] Activity timeline
- [ ] Import/export
- [ ] Duplicate detection

### Acceptance Criteria
- [ ] CRUD contacts and companies
- [ ] Custom field types (text, number, date, select)
- [ ] CSV import with mapping
- [ ] Activity logging
- [ ] Duplicate merge suggestions

## Feature 3: Sales Pipeline
**Priority:** P0

### User Story
As a sales manager, I want to track deals through stages.

### Description
Visual pipeline with customizable stages and automation.

### Components
- [ ] Kanban board
- [ ] Stage configuration
- [ ] Deal cards
- [ ] Drag-and-drop
- [ ] Stage automation
- [ ] Win/loss tracking

### Acceptance Criteria
- [ ] Custom pipeline stages
- [ ] Drag deals between stages
- [ ] Stage entry/exit rules
- [ ] Probability weighting
- [ ] Revenue forecasting

## Feature 4: Activity Tracking
**Priority:** P0

### User Story
As a sales rep, I want to log calls, emails, and meetings.

### Description
Comprehensive activity logging with calendar integration.

### Components
- [ ] Activity logger
- [ ] Email integration
- [ ] Calendar sync
- [ ] Call logging
- [ ] Note taking
- [ ] File attachments

### Acceptance Criteria
- [ ] Log multiple activity types
- [ ] Gmail/Outlook sync
- [ ] Calendar event creation
- [ ] File uploads to S3
- [ ] Rich text notes

## Feature 5: Reporting & Analytics
**Priority:** P1

### User Story
As a manager, I want insights into team performance.

### Description
Dashboards and reports with custom metrics.

### Components
- [ ] Dashboard builder
- [ ] Pre-built reports
- [ ] Custom report creator
- [ ] Data visualization
- [ ] Scheduled reports
- [ ] Export to PDF/Excel

### Acceptance Criteria
- [ ] 10+ pre-built reports
- [ ] Custom chart builder
- [ ] Filter and group data
- [ ] Automated email reports
- [ ] Real-time updates

## Feature 6: Automation & Workflows
**Priority:** P1

### User Story
As an admin, I want to automate repetitive tasks.

### Description
Visual workflow builder with triggers and actions.

### Components
- [ ] Workflow builder
- [ ] Trigger library
- [ ] Action library
- [ ] Condition logic
- [ ] Webhook support

### Acceptance Criteria
- [ ] 20+ triggers
- [ ] 30+ actions
- [ ] Conditional branching
- [ ] Webhook integrations
- [ ] Execution history

## Feature 7: Team Collaboration
**Priority:** P1

### User Story
As a team member, I want to collaborate on deals.

### Description
Comments, mentions, and team notifications.

### Components
- [ ] Comments system
- [ ] @mentions
- [ ] Notifications
- [ ] Activity feed
- [ ] Team dashboard

### Acceptance Criteria
- [ ] Comment on any record
- [ ] Mention team members
- [ ] In-app notifications
- [ ] Email notifications
- [ ] Notification preferences

## Feature 8: Mobile App
**Priority:** P2

### User Story
As a field sales rep, I want mobile access.

### Description
Responsive PWA with offline support.

### Components
- [ ] Mobile-optimized UI
- [ ] Offline data
- [ ] Push notifications
- [ ] Quick actions
- [ ] Voice notes

### Acceptance Criteria
- [ ] Works on iOS/Android
- [ ] Offline CRUD
- [ ] Background sync
- [ ] Push notifications
- [ ] Biometric auth

# 4. Page Structure

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Landing | Marketing site | No |
| /login | Login | Authentication | No |
| /dashboard | Dashboard | Main dashboard | Yes |
| /contacts | Contacts | Contact list | Yes |
| /contacts/[id] | Contact Detail | Single contact | Yes |
| /companies | Companies | Company list | Yes |
| /companies/[id] | Company Detail | Single company | Yes |
| /deals | Deals | Pipeline view | Yes |
| /deals/[id] | Deal Detail | Single deal | Yes |
| /activities | Activities | Activity feed | Yes |
| /reports | Reports | Analytics | Yes |
| /reports/[id] | Report Detail | Single report | Yes |
| /workflows | Workflows | Automation | Yes (Admin) |
| /settings | Settings | Configuration | Yes |
| /team | Team | Team management | Yes (Admin) |

# 5. API Requirements

- Authentication: /api/auth/*
- Contacts: /api/contacts/*
- Companies: /api/companies/*
- Deals: /api/deals/*
- Activities: /api/activities/*
- Reports: /api/reports/*
- Workflows: /api/workflows/*
- Webhooks: /api/webhooks/*
- Uploads: /api/upload/*
- Search: /api/search

# 6. Database Schema

Complex schema with:
- Organizations (multi-tenant)
- Users & Roles
- Contacts & Companies
- Deals & Stages
- Activities
- Workflows
- Reports
- Files
- Notifications

# 7. Authentication

- SAML 2.0
- OAuth 2.0 (Google, Microsoft)
- MFA (TOTP, SMS)
- RBAC with permissions
- API keys

# 8. UI/UX Guidelines

- Professional, clean design
- High information density
- Keyboard shortcuts
- Bulk actions
- Advanced filters
- Saved views

# 9. Performance

- Sub-100ms API responses
- Virtualized lists
- Optimistic updates
- Edge caching
- CDN for assets

# 10. Security

- SOC 2 compliance
- Data encryption at rest
- TLS 1.3
- Audit logging
- Data retention policies

# 11. Deployment

- Multi-region
- Blue-green deployments
- Feature flags
- A/B testing
- Monitoring & alerting

# 12. Timeline

Month 1: Core CRM (Contacts, Companies, Deals)
Month 2: Activities, Reports
Month 3: Workflows, Collaboration
Month 4: Mobile, Polish, Launch
