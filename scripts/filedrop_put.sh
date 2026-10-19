#!/bin/bash
# Put a file in Sork's FileDrop (written as www-data with its meta sidecar): filedrop_put.sh <file> "<Original Name.ext>" <mime>
set -e
F="$1"; NAME="$2"; MIME="${3:-image/png}"
B=$(basename "$F" | tr -s " \t" "__" | tr -cd "a-zA-Z0-9._-" | sed "s/\.\.*/./g"); SZ=$(stat -c %s "$F"); TS=$(date '+%Y-%m-%d %H:%M:%S')
D=$(mktemp -d); chmod 755 "$D"; cp "$F" "$D/$B"
printf '{\n    "original_name": "%s",\n    "type": "%s",\n    "uploaded_at": "%s",\n    "size": %s\n}\n' "$NAME" "${MIME//\//\\/}" "$TS" "$SZ" > "$D/$B.meta.json"
chmod 644 "$D"/*
docker cp "$D/$B" php8site:/tmp/ && docker cp "$D/$B.meta.json" php8site:/tmp/
docker exec php8site su -s /bin/bash www-data -c "cp '/tmp/$B' '/tmp/$B.meta.json' /var/www/filedrop/data/Sork/files/ && chmod 664 '/var/www/filedrop/data/Sork/files/$B' '/var/www/filedrop/data/Sork/files/$B.meta.json'"
docker exec php8site rm -f "/tmp/$B" "/tmp/$B.meta.json"; rm -rf "$D"
DEST=/home/serveperry/webserver/www/filedrop/data/Sork/files/$B
ls -l "$DEST"; [ "$(sha256sum < "$F")" = "$(sha256sum < "$DEST")" ] && echo "sha256 match $(sha256sum < "$F" | cut -c1-16)"
