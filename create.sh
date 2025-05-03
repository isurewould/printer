#!/bin/bash

# 1. Set your app path
APP_DIR="/home/pi/Desktop/photo_booth"  # <-- Adjust if your app is somewhere else
APP_SCRIPT="app.py"

# 2. Create the start script
echo "Creating start_photo_booth.sh..."
cat <<EOF > ~/start_photo_booth.sh
#!/bin/bash
cd $APP_DIR
python3 $APP_SCRIPT
EOF

chmod +x ~/start_photo_booth.sh
echo "start_photo_booth.sh created and made executable."

# 3. Create the Desktop shortcut
echo "Creating Desktop shortcut..."
cat <<EOF > ~/Desktop/PhotoBooth.desktop
[Desktop Entry]
Name=Photo Booth
Comment=Launch Photo Booth App
Exec=/home/pi/start_photo_booth.sh
Icon=camera
Terminal=true
Type=Application
Categories=Utility;
EOF

chmod +x ~/Desktop/PhotoBooth.desktop
echo "Desktop shortcut created and made executable."

echo "✅ All done! You can now double-click 'Photo Booth' on your desktop to launch the app."
