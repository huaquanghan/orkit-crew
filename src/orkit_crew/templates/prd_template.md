# Project Requirements Document

## Template for PRD-to-Product Pipeline

Copy this template and fill in your project details. The YAML frontmatter is required for automated processing.

---

```markdown
---
project_name: my-awesome-app
version: "1.0.0"
mode: greenfield
scope: mvp
stack:
  framework: nextjs
  language: typescript
  styling: tailwind
  ui_library: shadcn
  package_manager: pnpm
nextjs:
  router: app
  src_dir: true
complexity: auto
output_dir: ./output
---

# 1. Tổng quan / Overview

## Mô tả dự án / Project Description

Mô tả ngắn gọn về dự án và vấn đề nó giải quyết.
Brief description of the project and the problem it solves.

## Đối tượng ngườii dùng / Target Users

- User type 1: Description
- User type 2: Description

## Giả định và ràng buộc / Assumptions & Constraints

- Assumption 1
- Constraint 1

# 2. Mục tiêu / Goals

## Mục tiêu chính / Primary Goals

1. Goal 1
2. Goal 2

## KPIs / Success Metrics

- Metric 1: Target value
- Metric 2: Target value

# 3. Tính năng / Features

## Feature 1: [Feature Name]

**Priority:** P0 (Must have) / P1 (Should have) / P2 (Nice to have)

### User Story

Là một [loại ngườii dùng], tôi muốn [mục tiêu] để [lợi ích].
As a [user type], I want [goal] so that [benefit].

### Mô tả / Description

Mô tả chi tiết về tính năng.
Detailed description of the feature.

### Components

- [ ] Component 1
- [ ] Component 2
- [ ] Component 3

### Tiêu chí chấp nhận / Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Feature 2: [Feature Name]

**Priority:** P1

### User Story

...

# 4. Cấu trúc trang / Page Structure

## Routes

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| / | Home | Landing page | No |
| /login | Login | Authentication | No |
| /dashboard | Dashboard | Main dashboard | Yes |
| /profile | Profile | User profile | Yes |

## Navigation Structure

- Main Nav: Home, Dashboard, Profile
- Footer: Links, Copyright

# 5. API Requirements

## Endpoints

### GET /api/resource

- Description: Get resource list
- Auth: Required
- Response: `{ "data": [...] }`

### POST /api/resource

- Description: Create resource
- Auth: Required
- Body: `{ "name": "string" }`

# 6. Database Schema

## Tables

### users

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| email | String | Unique |
| name | String | |
| created_at | Timestamp | |

# 7. Authentication & Authorization

## Auth Method

- [ ] JWT
- [ ] Session
- [ ] OAuth (Google, GitHub, etc.)

## Roles

- Admin: Full access
- User: Limited access

# 8. UI/UX Guidelines

## Design System

- Colors: Primary, Secondary, Accent
- Typography: Font family, sizes
- Spacing: Consistent scale

## Responsive Breakpoints

- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

# 9. Performance Requirements

- Page load: < 3s
- Time to Interactive: < 5s
- Lighthouse score: > 90

# 10. Security Considerations

- [ ] Input validation
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Rate limiting

# 11. Deployment

## Environment Variables

```env
DATABASE_URL=
NEXTAUTH_SECRET=
NEXTAUTH_URL=
```

## Build Commands

```bash
pnpm install
pnpm build
pnpm start
```

# 12. Timeline

## Phases

### Phase 1: MVP (Weeks 1-2)

- [ ] Feature 1
- [ ] Feature 2

### Phase 2: Enhancement (Weeks 3-4)

- [ ] Feature 3
- [ ] Feature 4

# Appendix

## Notes

Additional notes or references.

## References

- [Link 1](url)
- [Link 2](url)
```

---

## Frontmatter Fields Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| project_name | string | Project identifier |
| version | string | Semantic version |
| mode | enum | `greenfield` or `extend` |
| scope | enum | `mvp` or `full` |
| stack | object | Technology stack config |
| complexity | enum | `auto`, `low`, `medium`, `high` |

### Stack Configuration

| Field | Type | Options |
|-------|------|---------|
| framework | string | `nextjs` |
| language | string | `typescript`, `javascript` |
| styling | string | `tailwind`, `css`, `scss` |
| ui_library | string | `shadcn`, `mui`, `chakra`, `none` |
| package_manager | string | `pnpm`, `npm`, `yarn`, `bun` |

### Next.js Configuration (optional)

| Field | Type | Description |
|-------|------|-------------|
| router | string | `app` or `pages` |
| src_dir | boolean | Use `src/` directory |
