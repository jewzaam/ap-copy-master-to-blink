# Flat Frame Matching

When no exact-date flat exists, the tool can find and use flats from other dates. This requires user confirmation to ensure equipment changes haven't invalidated older flats.

## Enabling Flexible Matching

```bash
ap-copy-master-to-blink <library> <blink> --flat-state ~/.ap-flat-state.yaml
```

Without `--flat-state`: exact date matches only.

With `--flat-state`: interactive date selection when no exact match exists.

## How It Works

1. **Exact match found** → use it, update state file cutoff to this date
2. **No exact match** → gather candidate flat dates (>= cutoff), prompt user

The state file tracks the **oldest valid flat date** per blink directory. Flats older than the cutoff are automatically excluded.

When an exact-match flat is used, the cutoff advances to that date. This keeps the cutoff current as new flats are taken.

**Critical**: Lights needing flats are processed in chronological order (oldest first). This ensures state file updates cascade correctly—choices made for earlier dates inform what's valid for later dates.

## Interactive Selection

When prompted, an interactive picker appears:

```
No exact flat for 2025-08-20 (filter: Ha)

  2025-08-17  (3 days older)
  2025-08-10  (10 days older)
  ────────────────────────────
▸ None of these (rig changed)
  ────────────────────────────
  2025-08-25  (5 days newer)
  2025-09-01  (12 days newer)

↑/↓ to move, Enter to select
```

"None" is centered and pre-selected. Move up to select older flats, down for newer flats. All candidates >= cutoff are shown.

**Selecting a date**: Uses that flat, updates cutoff to selected date.

**Selecting "none of these"**: Records the light date as cutoff (rig changed), marks flat missing.

## Quiet Mode

With `--quiet`: **exact date matches only**. No fallback selection, no prompting. Missing flats are logged and counted.

## Dry Run Mode

With `--dryrun`: full interactive behavior, but state file is not modified. Selections update an in-memory copy of the state, so subsequent processing within the same run behaves correctly. The actual state file remains unchanged.

## State File

Simple YAML mapping blink directory to cutoff date:

```yaml
"/data/RedCat51@f4.9+ASI2600MM/10_Blink": "2025-09-01"
```

Flats from the cutoff date or later are valid. The cutoff advances automatically when exact-match flats are used or when the user selects a flat interactively.
