# SmartVocab Design System

## Overview

SmartVocab is an intelligent English vocabulary learning system with a Klein Blue + Morandi hand-drawn aesthetic. The design language is warm, playful, and scholarly — combining the boldness of International Klein Blue with the muted elegance of Morandi colors and hand-drawn UI elements.

## Design Principles

1. **Warm Scholar** — Knowledge should feel inviting, not intimidating. Morandi muted tones create calm; Klein Blue provides intellectual authority.
2. **Hand-drawn Soul** — Asymmetric borders, dashed lines, and offset shadows give personality. Perfect symmetry feels corporate; slight imperfection feels human.
3. **Progressive Delight** — Start functional, reveal delight. Skeletons → content → micro-animations → celebration effects.
4. **Consistent Rhythm** — Spacing follows 4px base grid (4/8/12/16/24/32/48/64). Animation follows 150ms/300ms/500ms rhythm.

## Color System

| Token | Value | Role |
|-------|-------|------|
| `--klein-blue` | `#002FA7` | Primary brand, CTAs, active states |
| `--klein-light` | `#1a4fd0` | Hover/gradient endpoint |
| `--morandi-cream` | `#F5F0E8` | Page background (all pages) |
| `--morandi-beige` | `#E8DFD4` | Skeleton shimmer, subtle backgrounds |
| `--morandi-rose` | `#D4C4B5` | Dashed borders, dividers |
| `--morandi-lavender` | `#B8B4C8` | Hard shadows, subtle emphasis |
| `--accent-coral` | `#E07A5F` | Destructive actions, error states |
| `--accent-amber` | `#F2A03D` | Streak/combo highlights, warnings |
| `--accent-sage` | `#6B8E6B` | Success states, correct answers |

### Usage Rules
- Klein Blue: only for primary actions and active navigation — never for decorative fills
- Coral: only for errors/destructive — never for decoration
- Amber: only for gamification highlights (streak, combo) — never for standard UI
- Morandi tones: for all structural/decorative elements

## Typography

| Level | Size | Weight | Font | Use |
|-------|------|--------|------|-----|
| H1 | 1.5-2.5rem | 700 | Nunito | Page titles |
| H2 | 1.2-1.5rem | 600-700 | Nunito | Section headings |
| H3 | 1-1.2rem | 500-600 | Nunito | Card titles |
| Body | 0.875-1rem | 400 | Nunito | Main content |
| Caption | 0.75-0.85rem | 400-500 | Nunito | Metadata, labels |
| Decorative | 1-2rem | 400-600 | Caveat | Hand-letter decorations, example sentences |

### Rules
- Body text: never below 14px (0.875rem)
- Line height: minimum 1.4 for body text
- Caveat font: only for decorative text and example sentences — never for UI labels or buttons

## Spacing Scale

| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Icon-to-label gap |
| sm | 8px | Within-component spacing |
| md | 16px | Between related components |
| lg | 24-32px | Between sections |
| xl | 48-64px | Between major regions |

## Component Patterns

### Cards (sketch-card)
- Background: white
- Border-radius: asymmetric `20px 12px 20px 12px`
- Border: `2px dashed var(--morandi-rose)`
- Shadow: `3px 3px 0 var(--morandi-lavender)` (hard offset, no blur)
- Hover: `translateY(-4px) rotate(1deg)`, shadow expands to `5px 5px 0`

### Buttons
- Primary: Klein Blue background, white text, hand-drawn border-radius
- Secondary: White background, Klein Blue border
- Ghost: Transparent, text-only
- Destructive: Coral background, white text
- All buttons: `min-height: 44px` for touch targets
- Disabled state: `opacity: 0.5`, `cursor: not-allowed`, `pointer-events: none`

### Loading States
- Skeleton shimmer: `skeleton-box` class with gradient animation
- Spinner: dashed border Klein Blue spinner
- Text: Caveat font, "加载中..." with pulse animation
- Never show empty container — always show skeleton or loading state

### Empty States
- Icon (emoji or SVG) + title + description + action button/link
- Never just "暂无数据" — always provide next-step guidance

### Error States
- Distinct visual: coral/red border or background
- Plain language message (never technical details)
- Recovery suggestion ("请刷新重试", "检查网络连接")

## Animation

### Timing
- Micro: 150ms (hover, focus, toggle)
- Standard: 300ms (card lift, page transition, modal)
- Emphasis: 500ms (stagger entrance, celebration)
- Slow: 800ms+ (confetti, streak fire)

### Easing
- Default: `cubic-bezier(0.4, 0, 0.2, 1)` (material standard)
- Decelerate: `cubic-bezier(0.22, 1, 0.36, 1)` (entries)
- Accelerate: `cubic-bezier(0.4, 0, 1, 1)` (exits)

### Rules
- Always respect `prefers-reduced-motion: reduce` — disable non-essential animations
- Never animate layout properties (width, height, top, left) — use transform
- Stagger delays: 50-80ms between list items, max 5 items staggered

## Accessibility

- All interactive elements: visible focus indicator (`:focus-visible`)
- Icon-only buttons: `aria-label` required
- Form inputs: associated `<label>` (not placeholder-only)
- Color: never sole indicator of state — pair with icon/text
- Touch targets: minimum 44x44px
- Language: `<html lang="zh-CN">`

## Do

- Use CSS custom properties from `klein-morandi.css` for all colors/spacing
- Use `escapeHtml()` for all user-generated content in templates
- Use skeleton loading states for all async data
- Use `apiRequest()` for all API calls
- Use event delegation with `data-*` attributes (never inline handlers)
- Show loading/error/empty states for every data-fetching section

## Don't

- Hardcode colors — always use CSS variables
- Use emoji as the sole indicator of state (pair with text)
- Use inline `onclick` with dynamic data
- Show raw error messages or technical details to users
- Leave containers empty during loading
- Use more than 3 font sizes on a single screen
- Use Klein Blue for decorative/non-interactive elements
