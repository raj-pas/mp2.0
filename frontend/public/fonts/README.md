# Self-hosted fonts (locked decision #22d)

The v36 design uses three font families:

| Family | Files | Source |
|---|---|---|
| Fraunces (variable, 300/400/500/600, opsz 9..144) | `fraunces-variable.woff2` | https://fonts.google.com/specimen/Fraunces |
| Inter Tight (300/400/500/600/700) | `inter-tight-{300,400,500,600,700}.woff2` | https://fonts.google.com/specimen/Inter+Tight |
| JetBrains Mono (400/500/600) | `jetbrains-mono-{400,500,600}.woff2` | https://fonts.google.com/specimen/JetBrains+Mono |

## Why self-host

Locked decision #22d: drop Google Fonts CDN preconnect for privacy posture
+ to keep CSP `font-src` tight (only `'self'` + `data:`).

## Download instructions

Manual one-time setup (R0 polish):

```bash
# Pick your method; the goal is .woff2 files in this directory.

# Option A — google-webfonts-helper (https://gwfh.mranftl.com/fonts):
#   1. Search for each family
#   2. Choose latin charset, woff2 only, weights 300/400/500/600 (700 for Inter Tight)
#   3. Download zip; extract to this directory; rename to match the table above

# Option B — direct woff2 from fonts.gstatic.com (extract URLs from the
# Google Fonts CSS API by user-agent that returns woff2)
```

Once files are present, the `@font-face` declarations in `frontend/src/index.css`
pick them up automatically. Browser falls back to system fonts (Georgia for
serif, system-ui for sans, ui-monospace for mono) if files are missing — UI
still functions but loses the v36 visual fidelity.

## Verification

After downloading, run `npm run build` and confirm no 404s in browser
DevTools Network tab when loading the dev server.
