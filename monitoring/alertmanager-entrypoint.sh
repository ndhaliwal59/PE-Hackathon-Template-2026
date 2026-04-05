#!/bin/sh
set -e
u="${DISCORD_WEBHOOK_URL:-https://discord.com/api/webhooks/000000000000000000/invalid}"
awk -v u="$u" '{gsub("__DISCORD_WEBHOOK_URL__", u); print}' \
  /etc/alertmanager/alertmanager.yml.tpl > /tmp/alertmanager.yml
exec /bin/alertmanager --config.file=/tmp/alertmanager.yml
