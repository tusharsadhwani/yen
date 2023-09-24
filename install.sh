#!/usr/bin/env bash

# Copied from https://github.com/prefix-dev/pixi/blob/d8d2d8a/install/install.sh

set -euo pipefail

__wrap__() {

INSTALL_DIR="$HOME/.yen/bin"

REPO=tusharsadhwani/yen
PLATFORM=$(uname -s)
ARCH=$(uname -m)

if [[ $PLATFORM == "Darwin" ]]; then
  PLATFORM="apple-darwin"
elif [[ $PLATFORM == "Linux" ]]; then
  PLATFORM="unknown-linux-musl"
fi

if [[ $ARCH == "arm64" ]] || [[ $ARCH == "aarch64" ]]; then
  ARCH="aarch64"
fi

BINARY="yen-rs-${ARCH}-${PLATFORM}"

DOWNLOAD_URL=https://github.com/${REPO}/releases/latest/download/${BINARY}

printf "This script will automatically download and install yen for you.\nGetting it from this url: $DOWNLOAD_URL\nThe binary will be installed into '$INSTALL_DIR'\n"

if ! hash curl 2> /dev/null; then
  echo "error: you do not have 'curl' installed which is required for this script."
  exit 1
fi

TEMP_FILE=$(mktemp "${TMPDIR:-/tmp}/.pixi_install.XXXXXXXX")

cleanup() {
  rm -f "$TEMP_FILE"
}

trap cleanup EXIT

HTTP_CODE=$(curl -SL --progress-bar "$DOWNLOAD_URL" --output "$TEMP_FILE" --write-out "%{http_code}")
if [[ ${HTTP_CODE} -lt 200 || ${HTTP_CODE} -gt 299 ]]; then
  echo "error: '${DOWNLOAD_URL}' is not available"
  exit 1
fi

# Move pixi to the install directory
mkdir -p "$INSTALL_DIR"
cp "$TEMP_FILE" "$INSTALL_DIR/yen"

update_shell() {
    FILE=$1
    LINE=$2

    if [ -f "$FILE" ]; then
        if ! grep -Fxq "$LINE" "$FILE"
        then
            echo "Updating '${FILE}'"
            echo "$LINE" >> "$FILE"
        fi
    fi
}
case "$(basename "$SHELL")" in
    bash)
        if [ -f ~/.bash_profile ]; then
            BASH_FILE=~/.bash_profile
        else
            # Default to bashrc as that is used in non login shells instead of the profile.
            BASH_FILE=~/.bashrc
        fi
        LINE="export PATH=\$PATH:${INSTALL_DIR}"
        update_shell $BASH_FILE "$LINE"
        ;;

    fish)
        LINE="fish_add_path ${INSTALL_DIR}"
        update_shell ~/.config/fish/config.fish "$LINE"
        ;;

    zsh)
        LINE="export PATH=\$PATH:${INSTALL_DIR}"
        update_shell ~/.zshrc "$LINE"
        ;;

    *)
        echo "Unsupported shell: $(basename "$0")"
        ;;
esac

chmod +x "$INSTALL_DIR/yen"

echo "Please restart or source your shell."

}; __wrap__
