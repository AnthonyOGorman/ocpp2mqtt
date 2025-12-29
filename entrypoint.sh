#!/bin/sh
set -e

if [ "${RELAY_SERVER}" = "true" ]; then
  echo "Starting OCPP relay server..."
  ocpp-relay-server --cpms "${CPMS_URL}" &
  sleep 2
else
  echo "Relay server disabled"
fi

echo "Starting ocpp-snoop2mqtt..."
exec ocpp-snoop2mqtt \
  --snoop-socket="${SNOOP_SOCKET}" \
  --mqtt-broker-host="${MQTT_BROKER_HOST}" \
  --mqtt-broker-username="${MQTT_BROKER_USER}" \
  --mqtt-broker-password="${MQTT_BROKER_PASS}"