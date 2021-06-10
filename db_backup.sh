#!/bin/bash

file_name="/var/db/backup/$(date +%F)_sborka.db.7z"

7z a $file_name /var/db/bus.db

