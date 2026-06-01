# Plan: Hero Title Truncation Effect on Small Screens

## Context
The hero title ("GUIDO / SONCINI") currently uses `clamp(72px, 12vw, 200px)` which shrinks the font down to 72px on mobile — small enough to fit entirely on screen. The user wants the opposite: the text stays large and overflows the container, getting clipped at the right edge (as seen in the screenshot). The font stays as Syne 800.

## What to change
**File:** `index.html` — inline `<style>` block, `.hero-title` rule (around line 138)

### 1. Raise the font-size minimum so text overflows on mobile
```css
/* Before */
font-size: clamp(72px, 12vw, 200px);

/* After */
font-size: clamp(140px, 15vw, 200px);
```
At 375px viewport: `15vw = 56px` → clamped to **140px**, wide enough that both "GUIDO" and "SONCINI" extend past the right edge.

### 2. Prevent text wrapping
```css
white-space: nowrap;
```
Added to `.hero-title` so the spans never wrap to a second line — they just overflow.

## Why this works
`#hero` already has `overflow: hidden`, so any text that exceeds the container width is clipped automatically. No other changes needed.

## Verification
- Open `index.html` in browser at full width → title looks identical to current design
- Resize window to ~375px → "GUIDO" and "SONCINI" both overflow and clip at the right edge
- Check mid-size (~768px) → partial truncation of "SONCINI" only
