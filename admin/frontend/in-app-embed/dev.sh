#!/bin/sh
url="http://localhost:5173"
bench="${PILOT_BENCH:-$(pilot ls | sed 's/\x1b\[[0-9;]*m//g' | awk '$1 == "●" { print $2; exit }')}"

embed_url() {
  pilot -b "$bench" frappe set-config -g cloud_settings_embed_url "$1"
  pilot -b "$bench" frappe --site all clear-cache
}

embed_url "$url"
trap 'embed_url ""' EXIT
trap 'exit' INT TERM HUP

vite --port "${url##*:}" --strictPort
