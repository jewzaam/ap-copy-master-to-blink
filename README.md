# ap-copy-master-to-blink

[![Test](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/test.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/test.yml) [![Coverage](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/coverage.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/coverage.yml) [![Lint](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/lint.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/lint.yml) [![Format](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/format.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/format.yml) [![Type Check](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/typecheck.yml/badge.svg)](https://github.com/jewzaam/ap-copy-master-to-blink/actions/workflows/typecheck.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Copy master calibration frames from library to blink directories where light frames are located.

## Documentation

This tool is part of the astrophotography pipeline. For comprehensive documentation including workflow guides and integration with other tools, see:

- [Pipeline Overview](https://github.com/jewzaam/ap-base/blob/main/docs/index.md) - Full pipeline documentation
- [Workflow Guide](https://github.com/jewzaam/ap-base/blob/main/docs/workflow.md) - Detailed workflow with diagrams
- [ap-copy-master-to-blink Reference](https://github.com/jewzaam/ap-base/blob/main/docs/tools/ap-copy-master-to-blink.md) - API reference for this tool

## Overview

`ap-copy-master-to-blink` prepares light frames for manual review (blinking) by copying their required master calibration frames from the calibration library to the blink directories. This ensures calibration frames are in place before lights are moved to the data directory.

**Note**: This tool is designed for the **darks library workflow** with cooled cameras where master darks are stored in a permanent library and reused across sessions. It is **not designed** for nightly darks workflows with uncooled cameras.

## Workflow Position

1. **ap-move-master-to-library** - Organizes masters into calibration library
2. **Manual blinking review** - Visual inspection and culling of lights
3. **ap-copy-master-to-blink** - **(THIS TOOL)** Copies masters to blink directories
4. **ap-move-light-to-data** - Moves lights to data when calibration complete

**Important**: Calibration frames are NOT needed for blinking. They are needed before blinked lights can be moved to data.

## Installation

### From Git

```bash
pip install git+https://github.com/jewzaam/ap-copy-master-to-blink.git
```

### Development

```bash
git clone https://github.com/jewzaam/ap-copy-master-to-blink.git
cd ap-copy-master-to-blink
make install-dev
```

## Usage

```bash
# Basic usage
python -m ap_copy_master_to_blink <library_dir> <blink_dir>

# With dry-run (show what would be copied without copying)
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --dryrun

# Enable bias-compensated dark scaling (allows shorter dark exposures)
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --scale-dark

# Enable flexible flat matching with state persistence
python -m ap_copy_master_to_blink <library_dir> <blink_dir> --flat-state ~/.ap-flat-state.yaml
```

### Options

| Option | Description |
|--------|-------------|
| `library_dir` | Path to calibration library (supports env vars like `$VAR` or `${VAR}`) |
| `blink_dir` | Path to blink directory tree (supports env vars) |
| `--dryrun` | Show what would be copied without actually copying files |
| `--debug` | Enable debug logging |
| `--quiet`, `-q` | Suppress progress output |
| `--scale-dark` | Scale dark frames using bias compensation (allows shorter exposures). Default: exact exposure match only |
| `--flat-state PATH` | Path to flat state YAML file. Enables flexible flat date matching with interactive selection when no exact date match exists. |
| `--picker-limit N` | Max older/newer flat dates to show in interactive picker (default: 5). Only used with `--flat-state`. |
| `--date-dir-pattern PATTERN` | Regex pattern to match date directory where masters are copied (default: `"^DATE_.*"`). |

## Master Frame Matching

The tool matches calibration frames using FITS header metadata:

- **Dark Frames**: Match by camera, gain, offset, settemp, readoutmode, and exposure time
  - By default: exact exposure match only
  - With `--scale-dark`: allows shorter dark + bias frame combination
- **Flat Frames**: Match by camera, optic, filter, gain, offset, settemp, readoutmode, focallen
  - By default: exact date match only
  - With `--flat-state`: interactive selection from older/newer dates when no exact match exists
- **Bias Frames**: Match by camera, gain, offset, settemp, readoutmode (only copied when needed)

See the [detailed documentation](https://github.com/jewzaam/ap-base/blob/main/docs/tools/ap-copy-master-to-blink.md#master-frame-matching) for complete matching logic and current limitations.

## Directory Structure

### Expected Library Structure

```
library/
├── MASTER BIAS/
│   └── {camera}/
│       └── masterBias_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{settemp}_READOUTM_{readoutmode}.xisf
│
├── MASTER DARK/
│   └── {camera}/
│       └── masterDark_EXPOSURE_{exposure}_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{settemp}_READOUTM_{readoutmode}.xisf
│
└── MASTER FLAT/
    └── {camera}/
        └── {optic}/
            └── DATE_{YYYY-MM-DD}/
                └── masterFlat_FILTER_{filter}_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{settemp}_FOCALLEN_{focallen}_READOUTM_{readoutmode}.xisf
```

### Blink Directory Output

Masters are copied to the DATE directory (not scattered across filter subdirectories):

```
blink/
└── M31/
    └── DATE_2024-01-15/          # <-- ALL calibration frames HERE
        ├── masterDark_*.xisf
        ├── masterBias_*.xisf
        ├── masterFlat_FILTER_Ha_*.xisf
        ├── masterFlat_FILTER_OIII_*.xisf
        ├── FILTER_Ha/
        │   └── light_*.fits
        └── FILTER_OIII/
            └── light_*.fits
```

**Rationale**: All calibration frames in one place (DATE directory) makes them easier to find and manage. Darks are shared across filter subdirectories since they're exposure-dependent, not filter-dependent.
