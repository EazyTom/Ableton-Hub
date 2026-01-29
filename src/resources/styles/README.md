# Ableton Hub Style Configuration

This directory contains the centralized style configuration for Ableton Hub. All colors, fonts, spacing, and component-specific styles are defined here.

## Files

- **`style_config.json`** - Complete style configuration in JSON format
- **`__init__.py`** - Python module for loading and accessing style values

## Structure

### Colors

Colors are organized by category:
- **base**: Background and surface colors
- **accent**: Primary accent color (Ableton orange) and variants
- **text**: Text color variants
- **border**: Border colors
- **status**: Status indicator colors (success, warning, error, info)
- **location**: Location type colors
- **selection**: Selection highlight colors
- **scrollbar**: Scrollbar colors
- **export**: Export indicator colors

### Fonts

- **family**: Font family stack
- **sizes**: Named font sizes (tiny: 9px, small: 10px, compact: 11px, normal: 12px, large: 14px, title: 18px, header: 24px)
- **weights**: Font weight options

### Spacing

Named spacing values:
- **tight**: 2px
- **compact**: 4px
- **normal**: 6px
- **comfortable**: 8px
- **spacious**: 12px
- **large**: 16px
- **xlarge**: 20px

### Sizing

- **border_radius**: Small (3px), normal (4px), medium (6px), large (8px)
- **border_width**: Thin (1px), normal (2px), thick (3px)
- **padding**: Various padding presets
- **heights**: Component height presets
- **widths**: Component width presets

### Components

Component-specific style definitions:
- **search_bar**: Search bar styling
- **project_card**: Project card styling
- **sidebar**: Sidebar styling
- **table**: Table/list view styling
- **button**: Button variants
- **input**: Input field styling
- **combo**: Combo box styling

### Tempo Colors

Rainbow gradient configuration for tempo display (60-200 BPM range).

## Usage

### Loading the Config

```python
from resources.styles import get_style_config

config = get_style_config()
colors = config['colors']['base']
```

### Getting Colors

```python
from resources.styles import get_color

background = get_color('base', 'background')
accent = get_color('accent', 'accent')
```

### Getting Font Sizes

```python
from resources.styles import get_font_size

small_size = get_font_size('small')  # Returns 10
normal_size = get_font_size('normal')  # Returns 12
```

### Getting Component Styles

```python
from resources.styles import get_component_style

# Get entire component config
card_style = get_component_style('project_card')

# Get specific property
card_height = get_component_style('project_card', 'size.height')
```

### Using in Stylesheets

```python
from resources.styles import get_color, get_font_size, get_component_style
from ui.theme import AbletonTheme

# Option 1: Use theme (current approach)
color = AbletonTheme.COLORS['accent']

# Option 2: Use style config (future approach)
color = get_color('accent', 'accent')
```

## Migration Path

Currently, the app uses `AbletonTheme.COLORS` and `AbletonTheme.FONTS` directly. The style config provides a centralized location for all styles that can be:

1. **Loaded from JSON** - Easy to edit without code changes
2. **Validated** - Can add validation logic
3. **Extended** - Can add theme variants (light mode, custom themes)
4. **Documented** - Self-documenting structure

Future work could migrate the theme system to load from this config file.

## Adding New Styles

1. Add new values to `style_config.json`
2. Update this README if adding new categories
3. Consider updating `AbletonTheme` class to load from config

## Notes

- All color values are hex strings (e.g., "#ff764d")
- Font sizes are in pixels
- Spacing values are in pixels
- Border radius values are in pixels
- The config uses a flat structure for easy access
