#!/bin/bash
while IFS="|" read -r n c v s fl env; do [ -z "$n" ] && continue; /home/claude/rv/batch.sh "$n" "$c" "$v" "$s" "$fl" "$env"; done < /home/claude/rv/queue8.txt
echo Q8DONE
