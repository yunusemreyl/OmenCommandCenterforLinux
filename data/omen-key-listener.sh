#!/bin/bash
# HP Omen Key Listener (system service)
# Watches for KEY_PROG2 (Omen Key) events and toggles HP Manager GUI
#
# Dependencies: evtest

set -uo pipefail

# Find the HP WMI hotkeys input device
find_device() {
    for dir in /sys/class/input/event*/device; do
        if [ -f "$dir/name" ] && grep -q "HP WMI hotkeys" "$dir/name" 2>/dev/null; then
            echo "/dev/input/$(basename "$(dirname "$dir")")"
            return 0
        fi
    done
    return 1
}

# Retry device detection at boot (device may not be ready immediately)
MAX_RETRIES=30
RETRY_DELAY=2
DEV=""
for i in $(seq 1 $MAX_RETRIES); do
    DEV=$(find_device) && break
    echo "HP WMI hotkeys device not found, retrying ($i/$MAX_RETRIES)..."
    sleep $RETRY_DELAY
done

if [ -z "$DEV" ]; then
    echo "HP WMI hotkeys input device not found after $MAX_RETRIES attempts. Exiting."
    exit 1
fi

echo "Listening for Omen Key on $DEV ..."

# Launch HP Manager in the active graphical user's session
launch_for_user() {
    # Find the first logged-in graphical user
    local user uid
    for session in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
        local stype
        stype=$(loginctl show-session "$session" -p Type --value 2>/dev/null)
        if [ "$stype" = "x11" ] || [ "$stype" = "wayland" ]; then
            user=$(loginctl show-session "$session" -p Name --value 2>/dev/null)
            uid=$(id -u "$user" 2>/dev/null) || continue
            local display wayland_display xauth
            display=$(loginctl show-session "$session" -p Display --value 2>/dev/null)
            # Try to get WAYLAND_DISPLAY from user's environment
            wayland_display=""
            if [ -d "/run/user/$uid" ]; then
                wayland_display=$(find "/run/user/$uid" -maxdepth 1 -name "wayland-*" -printf '%f\n' 2>/dev/null | head -1)
            fi
            # Build environment for the GUI launch
            local env_vars="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus XDG_RUNTIME_DIR=/run/user/$uid"
            [ -n "$display" ] && env_vars="$env_vars DISPLAY=$display"
            [ -n "$wayland_display" ] && env_vars="$env_vars WAYLAND_DISPLAY=$wayland_display"
            echo "Launching hp-manager for user=$user (uid=$uid)"
            su - "$user" -c "env $env_vars hp-manager" &
            return 0
        fi
    done
    echo "No graphical session found, cannot launch GUI"
    return 1
}

# Use evtest to watch for KEY_PROG2 press events (value 1)
evtest "$DEV" 2>/dev/null | while IFS= read -r line; do
    if echo "$line" | grep -q "KEY_PROG2.*value 1"; then
        echo "Omen Key pressed — toggling HP Manager"
        launch_for_user
    fi
done
