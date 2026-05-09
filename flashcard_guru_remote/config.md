# Flashcard Guru Remote — Configuration

- **port**: TCP port the remote server listens on (default `39847`). Change only if you have a real conflict.
- **bound_interface**: IP address to bind to. `null` = auto-detect a private LAN interface. Set to a specific IP (e.g., `"192.168.1.5"`) if you have multiple network adapters and the wrong one is picked.
- **paired_devices**: List of phones paired with this Mac. **Edit this only to remove a stale entry.** Pair new devices via `Tools → Connect Phone (Flashcard Guru Remote)…`.

After changing `port` or `bound_interface`, restart Anki for changes to take effect.
