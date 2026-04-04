global:
  resolve_timeout: 5m

route:
  receiver: discord
  group_by: ["alertname"]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: discord
    discord_configs:
      - webhook_url: "__DISCORD_WEBHOOK_URL__"