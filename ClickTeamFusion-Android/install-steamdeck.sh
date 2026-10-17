#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
dll_path="${DLL_PATH:-$script_dir/xlive.dll}"
game_path="${1:-${GAME_PATH:-}}"
game_name="Mortal Kombat Arcade Kollection"

if [[ ! -f "$dll_path" ]]; then
    echo "Source DLL was not found: $dll_path"
    echo "Place xlive.dll next to this script or set DLL_PATH."
    exit 1
fi

find_game_path() {
    local candidates=(
        "$HOME/.steam/steam/steamapps/common/$game_name"
        "$HOME/.local/share/Steam/steamapps/common/$game_name"
        "$HOME/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/$game_name"
    )

    for candidate in "${candidates[@]}"; do
        if [[ -d "$candidate/BINARIES/WIN32" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

if [[ -z "$game_path" ]]; then
    if ! game_path="$(find_game_path)"; then
        echo "Could not find MKAK automatically."
        echo "Run with the game path, for example:"
        echo "  ./install-steamdeck.sh \"$HOME/.steam/steam/steamapps/common/$game_name\""
        exit 1
    fi
fi

target_dir="$game_path/BINARIES/WIN32"
target="$target_dir/xlive.dll"

if [[ ! -d "$target_dir" ]]; then
    echo "MKAK WIN32 folder was not found: $target_dir"
    exit 1
fi

if pgrep -f "MKHDGame.exe" >/dev/null 2>&1; then
    echo "MKHDGame.exe appears to be running. Close the game before installing."
    exit 1
fi

if [[ -f "$target" ]]; then
    backup="$target.backup-$(date +%Y%m%d-%H%M%S)"
    cp -f "$target" "$backup"
    echo "Backed up existing xlive.dll to: $backup"
fi

cp -f "$dll_path" "$target"
echo "Installed: $target"

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$target"
fi
