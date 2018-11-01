if [[ -z "$MSYSTEM" || "$MSYSTEM" = MINGW64 ]]; then
   source /local64/etc/profile2.local
elif [[ -z "$MSYSTEM" || "$MSYSTEM" = MINGW32 ]]; then
   source /local32/etc/profile2.local
fi
