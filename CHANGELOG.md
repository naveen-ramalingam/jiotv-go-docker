# Packaging releases

## v1.0.1

- Set explicit IPv4 DNS defaults in Compose (`1.1.1.1`, `8.8.8.8`) instead
  of inheriting a potentially unreachable host-advertised resolver.
- Allow resolver overrides through `JIOTV_DNS_PRIMARY` and
  `JIOTV_DNS_SECONDARY`; document LAN DNS and standalone Docker deployment.
- Document the DietPi DHCPv6 reboot failure and the verified persistent
  repair. The runtime image uses the same upstream JioTV Go v3.22.0.
- Refresh public image metadata and deployment examples.

## v1.0.0

- Initial ARM64/AMD64 container packaging, persistent login/TLS volumes,
  HTTPS, DRM, EPG, and GitHub image/release workflows.
