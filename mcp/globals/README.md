# Globals

Shared core stylistic variables for MarketState repos.

## Files

- `index.css`: aggregate CSS entrypoint for all global variables
- `colors.css`: color and status variables
- `fonts.css`: font families, sizes, weights, line heights, letter spacing
- `spacing.css`: spacing scale
- `radii.css`: border-radius scale
- `ratios.css`: aspect ratios and content widths
- `effects.css`: shadows and transitions
- `globals.json`: machine-readable mirror

## Usage

For CSS-based apps:

```css
@import "/path/to/globals/index.css";
```

Or import only the category you need:

```css
@import "/path/to/globals/colors.css";
@import "/path/to/globals/spacing.css";
```

## Guidance

- Use variables instead of hard-coded values in app styles.
- Prefer shared semantic colors like `--surface`, `--ink`, and `--muted`.
- Prefer spacing tokens like `--space-4` or `--space-8` instead of ad hoc pixel values.
- Add new globals here first if they are expected to be reused across repos.

## Suggested Next Step

Point frontend repos at `globals/index.css` and gradually replace local constants with shared variables.
