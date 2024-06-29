#!/usr/bin/env bash

# Copied from https://github.com/prefix-dev/pixi/blob/d8d2d8a/install/install.sh

__wrap__() {

  INSTALL_DIR="$HOME/.yen/bin"

  REPO=tusharsadhwani/yen
  PLATFORM=$(uname -s)
  ARCH=$(uname -m)

  if [ $PLATFORM = "Darwin" ]; then
    PLATFORM="apple-darwin"
  elif [ $PLATFORM = "Linux" ]; then
    PLATFORM="unknown-linux-musl"
  fi

  if [ $ARCH == "arm64" ] || [ $ARCH == "aarch64" ]; then
    ARCH="aarch64"
  fi

  BINARY="yen-rs-${ARCH}-${PLATFORM}"

  printf "This script will automatically download and install yen for you.\nGetting it from this url: $DOWNLOAD_URL\nThe binary will be installed into '$INSTALL_DIR'\n"

  if ! hash curl 2>/dev/null && ! hash wget 2>/dev/null; then
    echo "error: you do not have 'curl' or 'wget' installed which are required for this script."
    exit 1
  fi

  TEMP_FILE=$(mktemp "${TMPDIR:-/tmp}/.yen_install.XXXXXXXX")

  cleanup() {
    rm -f "$TEMP_FILE"
  }

  trap cleanup EXIT

  DOWNLOAD_FILE() {
    URL=$1
    OUTPUT=$2

    if hash curl 2>/dev/null; then
      HTTP_CODE=$(curl -SL --progress-bar "$URL" --output "$OUTPUT" --write-out "%{http_code}")
    elif hash wget 2>/dev/null; then
      wget -q --show-progress -O "$OUTPUT" "$URL"
      HTTP_CODE=$?
      if [ $HTTP_CODE -eq 0 ]; then
        HTTP_CODE=200
      else
        HTTP_CODE=500
      fi
    fi

    if [ ${HTTP_CODE} -lt 200 ] || [ ${HTTP_CODE} -gt 299 ]; then
      echo "error: '${URL}' is not available"
      exit 1
    fi
  }

  DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY}"
  DOWNLOAD_FILE "$DOWNLOAD_URL" "$TEMP_FILE"

  # Move yen to the install directory
  mkdir -p "$INSTALL_DIR"
  mv "$TEMP_FILE" "$INSTALL_DIR/yen"

  # Download userpath and microvenv too
  USERPATH_URL="https://yen.tushar.lol/userpath.pyz"
  DOWNLOAD_FILE "$USERPATH_URL" "$TEMP_FILE"
  mv "$TEMP_FILE" "$INSTALL_DIR/userpath.pyz"

  MICROVENV_URL="https://yen.tushar.lol/microvenv.py"
  DOWNLOAD_FILE "$MICROVENV_URL" "$TEMP_FILE"
  mv "$TEMP_FILE" "$INSTALL_DIR/microvenv.py"

  update_shell() {
    FILE=$1
    LINE=$2

    if [ -f "$FILE" ]; then
      if ! grep -Fxq "$LINE" "$FILE"; then
        echo "Updating '${FILE}'"
        echo "$LINE" >>"$FILE"
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
