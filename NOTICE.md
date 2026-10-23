# Upstream attribution

This image packages the unmodified, checksum-verified Linux executable of
[JioTV Go](https://github.com/JioTV-Go/jiotv_go), created by the JioTV Go
contributors. Upstream is licensed under Creative Commons Attribution 4.0
International; the complete supplied license is in `LICENSE.upstream`.

The exact upstream version, release URL, architecture-specific asset URLs,
sizes, and SHA-256 checksums are recorded in `upstream.lock.json`, also
included in the image at `/usr/share/jiotv-go/upstream.lock.json`.

This repository adds Docker packaging, persistent storage, TLS initialization,
non-root execution, tests, release automation, and deployment documentation.
It is not an official JioTV Go image and is not endorsed by Jio or the
upstream maintainers. No Jio credentials, playback sessions, or certificates
are included in the image.
