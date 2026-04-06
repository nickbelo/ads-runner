#!/usr/bin/env bash
set -euo pipefail

THEME_NAME="blank"
CURSOR_SIZE="16"
USER_HOME="${HOME}"
ICON_DIR="${USER_HOME}/.icons/${THEME_NAME}"
CURSOR_DIR="${ICON_DIR}/cursors"
BUILD_DIR="${USER_HOME}/.cache/${THEME_NAME}-cursor-build"
LABWC_ENV="${USER_HOME}/.config/labwc/environment"

echo "==> Installing required packages"
sudo apt update
sudo apt install -y x11-apps python3-pil

echo "==> Creating directories"
mkdir -p "${CURSOR_DIR}"
mkdir -p "${BUILD_DIR}"
mkdir -p "$(dirname "${LABWC_ENV}")"

echo "==> Writing theme index"
cat > "${ICON_DIR}/index.theme" <<'EOF'
[Icon Theme]
Name=blank
Comment=Invisible cursor theme
Inherits=Adwaita
EOF

echo "==> Creating transparent cursor image"
python3 - <<PY
from PIL import Image
img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
img.save("${BUILD_DIR}/blank.png")
PY

echo "==> Writing cursor source definition"
cat > "${BUILD_DIR}/arrow.in" <<EOF
16 0 0 ${BUILD_DIR}/blank.png 0
EOF

echo "==> Generating invisible base cursor"
xcursorgen "${BUILD_DIR}/arrow.in" "${CURSOR_DIR}/left_ptr"

echo "==> Creating cursor aliases"
cd "${CURSOR_DIR}"
for c in \
X_arrow \
alias \
all-scroll \
arrow \
based_arrow_down \
based_arrow_up \
bd_double_arrow \
bottom_left_corner \
bottom_right_corner \
bottom_side \
cell \
center_ptr \
circle \
col-resize \
color-picker \
context-menu \
copy \
cross \
cross_reverse \
crosshair \
default \
dnd-copy \
dnd-link \
dnd-move \
dnd-none \
dotbox \
down-arrow \
draft_large \
draft_small \
fleur \
grabbing \
hand \
hand1 \
hand2 \
left-arrow \
left_ptr \
left_ptr_watch \
left_side \
link \
move \
no-drop \
not-allowed \
openhand \
pencil \
pirate \
pointer \
question_arrow \
right-arrow \
right_ptr \
right_side \
row-resize \
sb_down_arrow \
sb_h_double_arrow \
sb_left_arrow \
sb_right_arrow \
sb_up_arrow \
sb_v_double_arrow \
size_all \
size_bdiag \
size_fdiag \
size_hor \
size_ver \
tcross \
text \
top_left_arrow \
top_left_corner \
top_right_corner \
top_side \
up-arrow \
vertical-text \
watch \
wayland-cursor \
xterm \
zoom-in \
zoom-out
do
    ln -sf left_ptr "${c}"
done

echo "==> Updating ~/.config/labwc/environment"
touch "${LABWC_ENV}"

python3 - <<PY
from pathlib import Path

env_file = Path("${LABWC_ENV}")
lines = env_file.read_text().splitlines() if env_file.exists() else []

wanted = {
    "XCURSOR_THEME": "${THEME_NAME}",
    "XCURSOR_SIZE": "${CURSOR_SIZE}",
}

out = []
seen = set()

for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        out.append(line)
        continue
    key, value = stripped.split("=", 1)
    if key in wanted:
        out.append(f"{key}={wanted[key]}")
        seen.add(key)
    else:
        out.append(line)

for key, value in wanted.items():
    if key not in seen:
        out.append(f"{key}={value}")

env_file.write_text("\\n".join(out) + "\\n")
PY

echo "==> Done"
echo
echo "Theme installed at: ${ICON_DIR}"
echo "labwc environment file: ${LABWC_ENV}"
echo
echo "Configured values:"
grep '^XCURSOR_' "${LABWC_ENV}" || true
echo

if [[ -n "${LABWC_PID:-}" ]]; then
    echo "==> LABWC_PID detected (${LABWC_PID}), reloading labwc"
    kill -HUP "${LABWC_PID}" || true
    echo "labwc reload signal sent."
elif LABWC_RUNNING_PID="$(pgrep -u "$(id -u)" labwc | head -n 1)"; [[ -n "${LABWC_RUNNING_PID}" ]]; then
    echo "==> labwc process detected (${LABWC_RUNNING_PID}), reloading labwc"
    kill -HUP "${LABWC_RUNNING_PID}" || true
    echo "labwc reload signal sent."
else
    echo "No active labwc process was detected for this user."
    echo "Log out and back in, or reboot, to apply the cursor theme."
fi

echo
echo "Verification after login:"
echo "  echo \$XCURSOR_THEME"
echo "  echo \$XCURSOR_SIZE"
