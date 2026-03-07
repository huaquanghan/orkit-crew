---
project_name: existing-ecommerce
version: 1.5.0
mode: extend
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
output_dir: ./output/ecommerce
---

# 1. Overview

Adding wishlist and review features to an existing e-commerce platform.
This PRD describes features to be added to the current codebase.

# 2. Goals

- Increase user engagement with wishlists
- Build trust through product reviews
- Improve product discovery

# 3. Features

## Feature 1: Product Wishlist
**Priority:** P0

### User Story
As a shopper, I want to save products to a wishlist for later.

### Description
Add wishlist functionality to existing product pages.

### Components
- [ ] Wishlist button on product cards
- [ ] Wishlist button on product detail
- [ ] Wishlist page
- [ ] Wishlist counter in header
- [ ] Move to cart functionality

### Acceptance Criteria
- [ ] Add/remove items from wishlist
- [ ] Persist wishlist across sessions
- [ ] Display wishlist count in header
- [ ] Share wishlist via URL
- [ ] Move items from wishlist to cart

## Feature 2: Product Reviews
**Priority:** P0

### User Story
As a shopper, I want to read and write product reviews.

### Description
Review system with ratings, photos, and moderation.

### Components
- [ ] Review display on product page
- [ ] Review submission form
- [ ] Star rating component
- [ ] Photo upload for reviews
- [ ] Helpful/unhelpful voting
- [ ] Review moderation dashboard

### Acceptance Criteria
- [ ] Display average rating
- [ ] Show rating distribution
- [ ] Submit review with rating and text
- [ ] Upload up to 5 photos per review
- [ ] Vote reviews as helpful
- [ ] Sort by newest/most helpful
- [ ] Filter by star rating

# 4. Page Structure

| Route | Page Name | Description | Auth Required |
|-------|-----------|-------------|---------------|
| /wishlist | Wishlist | User's saved items | Yes |
| /products/[id]/reviews | Reviews | All reviews for product | No |

# 5. API Requirements

- GET /api/wishlist
- POST /api/wishlist
- DELETE /api/wishlist/[id]
- GET /api/products/[id]/reviews
- POST /api/products/[id]/reviews
- PUT /api/reviews/[id]/helpful

# 6. Database Schema

New tables:
- Wishlists: id, user_id, product_ids[], created_at
- Reviews: id, product_id, user_id, rating, title, content, photos[], helpful_count, created_at

# 7. Authentication

Uses existing auth system.
Wishlist and review submission require login.

# 8. UI/UX Guidelines

Match existing design system:
- Use existing color palette
- Follow established spacing
- Reuse existing components where possible

# 9. Performance

- Lazy load reviews
- Cache wishlist count
- Optimize review images

# 10. Security

- Rate limit review submissions
- Moderate reviews before display
- Validate image uploads

# 11. Deployment

- Database migrations
- Feature flags for gradual rollout

# 12. Timeline

Week 1: Wishlist
Week 2: Reviews
