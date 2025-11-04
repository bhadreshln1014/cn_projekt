# Building Executables

This guide explains how to build standalone executables for the Video Conference application.

## Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

## Platform-Specific Instructions

### Windows

#### Build Client:
```batch
build_client.bat
```
Or manually:
```batch
pyinstaller build_client.spec --clean
```

#### Build Server:
```batch
build_server.bat
```
Or manually:
```batch
pyinstaller build_server.spec --clean
```

Output: `dist\VideoConferenceClient.exe` and `dist\VideoConferenceServer.exe`

### Linux/Mac

#### Build Client:
```bash
chmod +x build_client.sh
./build_client.sh
```
Or manually:
```bash
pyinstaller build_client.spec --clean
```

#### Build Server:
```bash
chmod +x build_server.sh
./build_server.sh
```
Or manually:
```bash
pyinstaller build_server.spec --clean
```

Output: `dist/VideoConferenceClient` and `dist/VideoConferenceServer`

## Output

After building, you'll find the executables in the `dist/` folder:
- **Client**: Single executable that users can run to join conferences
- **Server**: Single executable to host the conference server

## Notes

1. **File Size**: The executables will be large (50-150MB) because they include Python and all dependencies
2. **First Run**: May take longer to start as it extracts files
3. **Antivirus**: Some antivirus software may flag PyInstaller executables as suspicious (false positive)
4. **Platform Specific**: Build on the target platform (Windows .exe on Windows, Linux binary on Linux, etc.)
5. **Console Window**: 
   - Client has `console=False` (no console window)
   - Server has `console=True` (shows console for logging)

## Customization

Edit the `.spec` files to:
- Add an icon: Set `icon='path/to/icon.ico'`
- Change executable name: Modify `name='...'`
- Include data files: Add to `datas=[]`
- Show/hide console: Change `console=True/False`

## Troubleshooting

If the build fails:
1. Ensure all dependencies in `requirements.txt` are installed
2. Try building with `--debug all` flag
3. Check PyInstaller compatibility with your Python version
4. For missing modules, add them to `hiddenimports` in the spec file

## Distribution

You can distribute the executable from `dist/` folder. Users don't need Python installed to run it.
