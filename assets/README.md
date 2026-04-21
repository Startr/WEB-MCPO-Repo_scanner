# TodoScope Assets

## todoscope.icns

The macOS app icon (`todoscope.icns`) needs to be generated from the telescope emoji (U+1F52D).

To create the icon:

1. Design or export a 1024x1024 PNG of the telescope emoji
2. Use `iconutil` to convert it:

```bash
mkdir todoscope.iconset
# Add all required sizes (16, 32, 64, 128, 256, 512, 1024) as PNG files
# e.g. icon_16x16.png, icon_16x16@2x.png, icon_32x32.png, etc.
iconutil -c icns todoscope.iconset -o todoscope.icns
```

The `.icns` file is referenced by the PyInstaller spec (`todoscope.spec`) for the macOS `.app` bundle.
