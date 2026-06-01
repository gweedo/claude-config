# Plan: Migrate CV from single-file HTML to Vite + React + TypeScript

## Context

The current site is a single 1.8 MB `index.html` containing inlined CSS, inlined React/JSX transformed by Babel-standalone at runtime, and base64-encoded assets decoded by a custom in-browser "bundler" with an "Unpacking..." overlay. It works but is hard to edit, slow to first paint (Babel runs in the browser), and has no component boundaries, type safety, or hot reload.

Goal: move to a **proper Node-based build pipeline** that compiles a normal multi-file static site, deploys cleanly to GitHub Pages, and follows industry best practices so you can learn modern frontend project structure.

**GitHub Pages compatibility check:** Pages serves only static files — no Node runtime. Vite's `vite build` produces a static `dist/` folder (HTML + hashed JS/CSS chunks + assets) that Pages serves directly. Fully supported. The existing workflow in `.github/workflows/deploy.yml` will need its build step updated to run `npm ci && npm run build` and upload `dist/` instead of the repo root.

## Stack (decided)

- **Vite 5** — bundler + dev server
- **React 18** + **TypeScript** — component model + type safety
- **CSS Modules** (`.module.css`) — scoped styles, zero extra deps
- **Node 20 LTS** — runtime for tooling only (not in production)

## Target project structure

```
CV/
├── public/                       # Static files copied verbatim to dist/
│   ├── profile_face.jpg          # Moved from repo root
│   ├── CV-GuidoSoncini-EN.pdf    # If you want it downloadable
│   └── favicon.svg
├── src/
│   ├── main.tsx                  # React entry point (ReactDOM.createRoot)
│   ├── App.tsx                   # Root component
│   ├── index.css                 # Global resets, CSS vars (colors, fonts)
│   ├── components/
│   │   ├── Hero/
│   │   │   ├── Hero.tsx
│   │   │   └── Hero.module.css
│   │   ├── Experience/
│   │   ├── Skills/
│   │   ├── Education/
│   │   └── Contact/
│   ├── data/
│   │   └── cv.ts                 # Typed CV content (single source of truth)
│   ├── types/
│   │   └── cv.types.ts           # TypeScript interfaces for CV data
│   └── assets/                   # Imported by components (hashed at build)
├── index.html                    # Vite entry HTML (small — just <div id="root">)
├── vite.config.ts                # Build config, base path for GH Pages
├── tsconfig.json
├── tsconfig.node.json
├── package.json
├── .gitignore                    # Add node_modules, dist
├── .nvmrc                        # Pin Node 20
└── .github/workflows/deploy.yml  # Updated to build + upload dist/
```

**Why this layout (the "learning" part):**

- `public/` vs `src/assets/`: files in `public/` are copied as-is and referenced by absolute URL (`/profile_face.jpg`); files in `src/assets/` are imported in code (`import face from './assets/face.jpg'`) so Vite hashes them for cache-busting. Rule: PDFs and shareable links go in `public/`; images used inside components go in `src/assets/`.
- **One folder per component**, co-locating the `.tsx` and its `.module.css`. Easier to delete/rename a component cleanly.
- `data/cv.ts` separates **content from presentation** — your CV text lives in one typed object, the components render it. Editing your CV later means editing one file, not hunting through JSX.
- `types/` mirrors the data shape, enforcing that every CV entry has the same fields.

## Migration steps (execution order)

1. **Initialize project** in a new branch (`feat/vite-migration`):
   - `npm create vite@latest . -- --template react-ts` (in an empty subdir, then merge files back)
   - Install: nothing extra — React, TS, Vite come with the template.

2. **Configure `vite.config.ts`** with `base: '/CV/'` (assuming repo name `CV`; adjust if different or if a custom domain is added):
   ```ts
   export default defineConfig({ plugins: [react()], base: '/CV/' });
   ```

3. **Extract content from current `index.html`** into `src/data/cv.ts`:
   - Open the existing inline JSX in `index.html`, copy the data objects (experience entries, skills, etc.) into a typed structure in `cv.ts`.
   - Define the matching interfaces in `src/types/cv.types.ts` (e.g., `Experience`, `SkillCategory`, `EducationEntry`).

4. **Extract sections into components** (one at a time, in order):
   - `Hero` → `Experience` → `Skills` → `Education` → `Contact`.
   - For each, copy the JSX from `index.html`, move associated CSS rules from the inline `<style>` block into the component's `.module.css`, replace class names with `styles.className`, and import the component into `App.tsx`.

5. **Move global styles** (resets, CSS variables, body/typography) into `src/index.css`. Imported once in `main.tsx`.

6. **Replace asset references**: move `profile_face.jpg` into `public/` (keep the same filename) or `src/assets/` and import it.

7. **Delete the old bundler scaffolding** — `__bundler/manifest`, `__bundler/template`, `__bundler/ext_resources`, the "Unpacking..." overlay, the Babel-standalone `<script>`. None of this is needed; Vite handles JSX/asset bundling at build time.

8. **Update `.github/workflows/deploy.yml`**:
   - Add `actions/setup-node@v4` with Node 20.
   - Run `npm ci && npm run build`.
   - Upload `./dist` (not `.`) via `actions/upload-pages-artifact@v3`.

9. **Update `.gitignore`**: add `node_modules/` and `dist/`.

10. **Add `package.json` scripts** (Vite template gives these; just confirm):
    - `dev` → local hot-reload at `http://localhost:5173`
    - `build` → produces `dist/`
    - `preview` → serves the built `dist/` locally to sanity-check before push

## Critical files

- [index.html](index.html) — source of truth for content/styles to extract (1.8 MB, 183 lines of HTML wrapping inlined React + bundler)
- [.github/workflows/deploy.yml](.github/workflows/deploy.yml) — Pages deployment; needs build step added
- [plan/PLAN.md](plan/PLAN.md) — auto-updated each turn per existing convention

## Verification

End-to-end test before opening the PR:

1. `npm install` succeeds, `npm run dev` opens the CV in the browser identical to current production.
2. `npm run build` produces a `dist/` folder under ~500 KB total (vs current 1.8 MB single file).
3. `npm run preview` serves `dist/` and the page renders identically — including the profile photo and mobile layout (test at 375 px viewport, matching the current `fix/mobile-responsive` work).
4. Open PR to `main`; the GitHub Actions workflow builds and deploys to Pages; the live site loads without the "Unpacking..." overlay and shows hashed asset filenames in the network tab.
5. Lighthouse score should improve vs current (no runtime Babel = faster TTI).

## What you'll learn from doing this

- **Build vs runtime**: today Babel transforms JSX in the browser on every load; after migration, Vite does it once at build time. This is the single most important concept in modern frontend.
- **Module system**: `import`/`export` replaces "everything in one file".
- **Component composition**: `<App>` mounts `<Hero>`, `<Experience>`, etc. — each owns its markup, styles, and types.
- **Type-driven development**: editing `cv.ts` with a typo (e.g., missing field on an `Experience`) becomes a compile error, not a runtime surprise.
- **Static deployment pipeline**: Node tooling produces artifacts; GitHub Pages serves them. The Node runtime never touches production.
