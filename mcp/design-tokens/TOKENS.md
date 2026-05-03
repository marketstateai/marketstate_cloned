# Design Tokens

Shared visual tokens for MarketState repos.

## Files

- `tokens.css`: drop-in CSS custom properties for static sites and frontend apps
- `tokens.json`: machine-readable mirror for scripts, build tooling, or non-CSS consumers

## Current Token Groups

- `background`
  - `--bg`: default app background
  - `--surface`: primary panel/card background
  - `--surface-2`: secondary raised surface
  - `--surface-3`: tertiary or interactive surface
- `border`
  - `--line`: standard border color
  - `--line-soft`: softer border for low-emphasis containers
  - `--white-line`: translucent light divider for dark UIs
- `text`
  - `--ink`: default body text on dark surfaces
  - `--ink-strong`: high-emphasis text
  - `--muted`: secondary/supporting text
  - `--muted-deep`: stronger muted text, labels, and subtle emphasis
- `accent`
  - `--accent`: default neutral accent
  - `--accent-strong`: strongest neutral accent
  - `--cyan`: informational/highlight accent
  - `--green`: positive status
  - `--rose`: negative or warning-adjacent status
- `effects`
  - `--shadow`: default elevated container shadow

## Usage

In CSS:

```css
@import "./design-tokens/tokens.css";

.card {
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow);
}
```

In another repo, either:

1. Copy this folder as the shared source of truth for now.
2. Or publish/symlink it later as a package such as `@marketstate/design-tokens`.

## Rules

- Use semantic token names, not hard-coded hex values, in app code.
- Prefer `--ink` and `--ink-strong` for text instead of raw white.
- Prefer `--surface`, `--surface-2`, and `--surface-3` for layering instead of inventing new dark grays.
- If a new token is needed in one repo, add it here first and document its intent.

## Next Step

If this becomes shared across multiple repos, add:

- a versioned package name
- a changelog
- generated outputs for CSS, JS/TS, and design-tool export
