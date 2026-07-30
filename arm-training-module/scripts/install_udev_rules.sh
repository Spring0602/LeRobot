#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_RULES="${SCRIPT_DIR}/../configs/99-so101.rules"
TARGET_RULES="/etc/udev/rules.d/99-so101.rules"

if [[ ! -f "${SOURCE_RULES}" ]]; then
  echo "Missing rules file: ${SOURCE_RULES}" >&2
  exit 2
fi

python3 "${SCRIPT_DIR}/device_config.py"
sudo install -o root -g root -m 0644 "${SOURCE_RULES}" "${TARGET_RULES}"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty

echo "Installed ${TARGET_RULES}"
echo "Reconnect the four controllers, then run:"
echo "python3 ${SCRIPT_DIR}/device_config.py --live"
