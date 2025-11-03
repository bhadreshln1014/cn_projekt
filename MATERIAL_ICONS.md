# Material Design Icons Setup

## Overview
The application now supports Material Design icons using the **QtAwesome** library. This provides professional, crisp icons instead of emoji symbols.

## Installation

To enable Material Design icons, install QtAwesome:

```bash
pip install qtawesome==1.3.1
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Features

When QtAwesome is installed, the following UI elements will use Material Design icons:

### Bottom Control Bar
- **Microphone** (`mdi.microphone` / `mdi.microphone-off`)
- **Camera** (`mdi.video` / `mdi.video-off`)
- **Screen Share** (`mdi.monitor-share`)
- **Leave Call** (`mdi.phone-hangup`)

### Right Panel Toggles
- **People** (`mdi.account-group`)
- **Chat** (`mdi.message-text`)
- **Files** (`mdi.folder`)
- **Settings** (`mdi.cog`)

### Chat Panel
- **Send Message** (`mdi.send`)

### File Panel
- **Download** (`mdi.download`)
- **Delete** (`mdi.delete`)

### Settings Panel
- **Refresh Devices** (`mdi.refresh`)

## Fallback Behavior

If QtAwesome is not installed, the application will automatically fall back to emoji icons:
- 🎤 Microphone
- 📹 Camera
- 🖵 Screen Share
- 📞 Leave Call
- 👥 People
- 💬 Chat
- 📁 Files
- ⚙️ Settings
- ➤ Send
- And others...

## Icon Customization

To customize icons, edit the `get_icon()` method in `src/client/client.py`:

```python
def get_icon(self, icon_name, color='#e8eaed', size=None):
    """Get Material Design icon using qtawesome or fallback to text"""
    if HAS_QTAWESOME:
        icon_map = {
            'mic': 'mdi.microphone',
            'videocam': 'mdi.video',
            # Add more mappings here
        }
        # ...
```

### Available Icon Sets in QtAwesome
- **Material Design Icons** (`mdi.*`) - Recommended
- **Font Awesome** (`fa.*`, `fa5.*`)
- **Elusive Icons** (`ei.*`)
- **And more...**

Browse icons at:
- Material Design: https://pictogrammers.com/library/mdi/
- Font Awesome: https://fontawesome.com/icons

## Benefits

✅ **Professional appearance** - Clean, consistent icon design  
✅ **Scalable** - Icons look crisp at any size  
✅ **Customizable colors** - Integrate with dark theme  
✅ **Platform-independent** - Works on Windows, macOS, Linux  
✅ **Accessible** - Better readability than emojis
