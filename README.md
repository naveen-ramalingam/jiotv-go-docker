# JioTV Go — Docker packaging

Repository: <https://github.com/naveen-ramalingam/jiotv-go-docker>

- Packaging release: **v1.0.1**
- Upstream application: **JioTV Go v3.22.0**
- Image: **`ghcr.io/naveen-ramalingam/jiotv-go-docker:1.0.1`**
- Platforms: **linux/arm64** (Raspberry Pi 5) and **linux/amd64**

GitHub Actions builds and publishes the image to GitHub Container Registry.
The repository and container package are public. Cloning the source and
pulling the image require no GitHub sign-in or registry token. The image
links to this repository through its OCI source label.

## Included

- Official upstream executables pinned by release, architecture, size, and
  SHA-256 in `upstream.lock.json`.
- DRM and EPG enabled by default. JioTV Go refreshes EPG automatically each day.
- HTTPS on container port 5002, with a per-installation certificate generated
  on first startup and preserved across restarts.
- Persistent `/data` for login state and programme guide, and `/tls` for TLS.
- Application process runs as UID/GID 10001 with no effective capabilities.
  A short root entrypoint prepares volume ownership and then drops privileges.
- Read-only container root filesystem, bounded Docker logs, TLS/static readiness health check,
  restart policy, and Compose deployment.
- Explicit, configurable IPv4 DNS in Compose so a broken host-advertised
  IPv6 resolver is not inherited by the application after reboot.
- Daily upstream discovery in GitHub Actions at **04:15 IST / 22:45 UTC**.
  A new stable upstream version advances the packaging patch version,
  refreshes both architecture checksums, and dispatches a GitHub image build.
  GitHub scheduled workflows may start later than their nominal time.

Certificates, login state, OTPs, tokens, local `.env`, and data volumes are
created at deployment time. The build context uses an allowlist and contains
none of those installation secrets.

## Pull the image

Pull the versioned image without signing in:

```sh
docker pull ghcr.io/naveen-ramalingam/jiotv-go-docker:1.0.1
```

The `latest` tag is also available; use a version tag or release digest for
repeatable deployments. JioTV still requires your own Jio login after startup.

## Deploy with Compose

Download the deployment archive from the GitHub release, or clone this
public repository:

```sh
git clone https://github.com/naveen-ramalingam/jiotv-go-docker.git
cd jiotv-go-docker
cp .env.example .env
```

Edit `.env` for the host's LAN address and available port. The example is:

```dotenv
IMAGE=ghcr.io/naveen-ramalingam/jiotv-go-docker:1.0.1
BIND_IP=192.168.1.50
HOST_PORT=5002
TZ=Asia/Kolkata
JIOTV_DNS_PRIMARY=1.1.1.1
JIOTV_DNS_SECONDARY=8.8.8.8
JIOTV_EPG=true
JIOTV_DRM=true
JIOTV_TLS_NAMES=192.168.1.50,dietpi.lan
```

`localhost` and `127.0.0.1` are always included in generated certificates so
the internal health check can validate TLS. `JIOTV_TLS_NAMES` adds the
addresses and hostnames clients will use. If `.env` is absent, Compose binds
only to loopback by default.

Use the new Pi's actual IP address for `BIND_IP` and `JIOTV_TLS_NAMES`.

Then:

```sh
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail 50
```

Open <https://192.168.1.50:5002/>, accept or trust the local certificate, and
sign in with the Jio mobile number and OTP. Browser DRM playback requires
HTTPS; upstream lists Chrome and Firefox as supported browsers. Available
channels depend on the account's entitlements.

The default volumes are `jiotv-go-data` and `jiotv-go-tls`. Keep both when
recreating the container. Changing `JIOTV_TLS_NAMES` does not replace an
existing certificate automatically; renew the certificate deliberately if
the deployment address changes.

## DNS and reboot behaviour

Release **v1.0.1** adds explicit Compose DNS defaults: `1.1.1.1` and `8.8.8.8`.
They are independent of the host's advertised resolver list and remain in
the container configuration across reboots. Set `JIOTV_DNS_PRIMARY` and
`JIOTV_DNS_SECONDARY` in `.env` to change them. If the LAN blocks public DNS,
or the deployment needs the router's resolver, set both to a working LAN
DNS address. The existing DietPi deployment uses its router at `192.168.1.1`.

The original DietPi reboot failure was a DHCPv6 event overwriting host DNS
with an unreachable IPv6 resolver. Login data and the running container were
intact. The fix was verified through a full host reboot, logged-in channel
listing, XMLTV, and Star Vijay HD / Sun Music HD stream-manifest requests.

These DNS settings belong to **Compose**, not the image. When creating a
container through another tool or `docker run`, set equivalent DNS options,
for example `--dns 1.1.1.1 --dns 8.8.8.8`. An image alone does not control
Docker's DNS configuration. The host also needs working DNS to download
images; Compose's settings only apply after the container is created.

Check the chosen resolver from the host, then from the running container:

```sh
nslookup jiotvapi.media.jio.com 1.1.1.1
docker compose exec jiotv-go nslookup jiotvapi.media.jio.com
```

After restarting the Pi, check `docker compose ps`, open the logged-in web
interface, and play a live channel. Persistent volumes retain the account
session, certificate and EPG. Provider outages, account expiry and blocked
network access can still affect playback independently of this DNS fix.

## Existing Pi installation and migration

The original Pi installation uses a native `jiotv-go.service` on port 5002
and a daily `jiotv-go-update.timer`. Docker tests use a different,
loopback-only port and disposable volumes.

To run a fresh Docker instance alongside it, choose another port, for example
`HOST_PORT=5003`. A fresh volume starts a separate login session.

For a deliberate migration preserving the current login and EPG:

1. Make a protected backup of `/var/lib/jiotv-go/`, `/etc/jiotv-go/`, and the
   native systemd units, following the existing Pi setup guide.
2. Stop the native updater timer and let an in-progress updater finish.
3. Stop the native application so its state can be copied consistently.
4. Create the two Docker volumes. Copy the **contents** of the native
   `/var/lib/jiotv-go/` into `jiotv-go-data`, and `server.crt` plus `server.key`
   from `/etc/jiotv-go/` into `jiotv-go-tls`. Keep all files in the data folder,
   rather than selecting a historical credential filename.
5. Start Compose on the original port. The entrypoint adjusts volume
   ownership for UID/GID 10001. Validate browser login state, playback,
   playlist, and EPG before disabling the native application at boot.

The Docker image uses immutable application files; upgrading means replacing
the container image. The native host binary updater is not used inside it.

## TiviMate

All channels grouped by category and language:

```text
https://192.168.1.50:5002/playlist.m3u?q=high&c=split
```

Language-only groups such as Tamil, Hindi, and English:

```text
https://192.168.1.50:5002/playlist.m3u?q=high&c=language
```

Tamil-only channels, with category groups:

```text
https://192.168.1.50:5002/playlist.m3u?q=high&c=split&l=Tamil
```

Programme guide:

```text
https://192.168.1.50:5002/epg.xml.gz
```

In TiviMate, add an M3U playlist and assign the EPG source to it. Enable the
TV app's EPG refresh as well. After editing a playlist URL, update the playlist.
Adjust the host port in these URLs if Compose uses a different host port.

The recommended URLs include subscription-labelled channels. Adding
`sub=hide` hides them even when the account can play them; this previously
hid Sun Music HD and Star Vijay HD in the Pi setup.

A self-signed certificate may be rejected by a TV app. It needs a certificate
the app trusts, or a separately configured LAN proxy, if SSL import fails.
DRM playback also depends on the player/device. A successful playlist import
does not validate every stream. The checked upstream playlist contains no
TiviMate catch-up attributes. In the web UI, turn Catchup off or choose
Watch Live for live viewing; Sun Music HD reports that catch-up is unavailable.

## Updates and releases

The packaging version is independent from the upstream application version.
`v1.0.1` packages upstream `v3.22.0`; the lock file records the mapping.

The GitHub workflow `Check upstream stable release` runs daily at 22:45 UTC
and can also be run manually. For a newer stable upstream release it:

1. Requires official ARM64 and AMD64 assets with GitHub SHA-256 digests.
2. Updates `upstream.lock.json` and increments the packaging patch version.
3. Commits those files, creates the new `v*` tag, and explicitly dispatches
   `release.yml`. The explicit dispatch is necessary because pushes made by
   `GITHUB_TOKEN` do not trigger another workflow by themselves.
4. The release workflow validates the project, builds and smoke-tests a
   native image's local HTTPS/static readiness and persistence, then builds
   and pushes the ARM64/AMD64 manifest on GitHub.
5. After publishing succeeds, it creates a GitHub release with the image
   digest, upstream lock, and deployment archive.

Only the short-lived repository `GITHUB_TOKEN` is used in these workflows.
The workflow jobs declare `contents`, `actions`, and `packages` permissions
for their specific operations. No personal token is stored as a repository
secret. GitHub Actions used by the project are pinned to verified commits.

To release packaging changes manually, edit `VERSION`, commit the changes,
and push the matching tag:

```sh
git add VERSION
git commit -m 'Release packaging v1.0.2'
git tag v1.0.2
git push origin main
git push origin v1.0.2
```

Set `VERSION` to `1.0.2` before running that example. The tag must point to
the intended commit and match the file. The workflow refuses a mismatch.
Use the Actions UI to rerun a failed build after resolving its error.

Publishing an image does not replace running containers automatically.
Compose is version-pinned and explicitly opted out of the host's Watchtower.
To deploy a chosen release, update `IMAGE` in `.env`, then:

```sh
docker compose pull
docker compose up -d
docker compose ps
```

Back up the data and TLS volumes before upgrading. To roll back, restore the
previous image reference and, if a new version changed its state format,
restore the matching data backup. Each GitHub release includes an immutable
`ghcr.io/...@sha256:...` image reference.

## Backups and logs

Stop the service for a consistent volume backup. Store archives privately:

```sh
mkdir -m 0700 -p backups
docker compose stop
docker run --rm -v jiotv-go-data:/source:ro -v "$PWD/backups:/backup" \
  alpine:3.24.3 tar -C /source -czf /backup/data.tar.gz .
docker run --rm -v jiotv-go-tls:/source:ro -v "$PWD/backups:/backup" \
  alpine:3.24.3 tar -C /source -czf /backup/tls.tar.gz .
chmod 0600 backups/*.tar.gz
docker compose start
```

The data archive contains login state; the TLS archive contains the private
certificate key. Use timestamped filenames for multiple backup generations.
Restore into stopped volumes before starting the matching application image.

Logs are available through `docker compose logs`. The default newly created
application file-log path points to `/dev/null`, while stdout is collected
by Docker with 10 MiB × 3 file rotation. A regular file deliberately supplied
at `/data/logs/jiotv_go.log` is preserved and needs its own rotation policy.

## Local build and tests

GitHub builds are the release source. For local development with Buildx:

```sh
docker buildx build --platform linux/arm64 --load \
  --build-arg PACKAGE_VERSION=1.0.1 --build-arg UPSTREAM_VERSION=v3.22.0 \
  --tag jiotv-go-docker:dev .
python3 -m unittest discover -s tests -v
python3 scripts/smoke_test.py jiotv-go-docker:dev --enable-epg
```

Select `linux/amd64` on an AMD64 machine. On the existing Pi, which does not
have Buildx installed, a validation build can use the supported legacy path:

```sh
DOCKER_BUILDKIT=0 docker build --build-arg TARGETARCH=arm64 \
  --build-arg PACKAGE_VERSION=1.0.1 --build-arg UPSTREAM_VERSION=v3.22.0 \
  --tag jiotv-go-docker:dev .
```

Tests use disposable named volumes and loopback-only random ports. They
check version, TLS verification, embedded JavaScript delivery, non-root
execution, capabilities, persistent state, and certificate reuse across
restarts. `--integration` additionally checks the live homepage and M3U;
`--enable-epg` includes those checks and validates generated XMLTV.

GitHub-hosted runner requests to the external Jio API returned HTTP 450
during the initial validation. The GitHub smoke test therefore checks
self-contained container readiness. Live M3U/EPG integration is checked on
the Pi where those requests succeed. The runtime health check also measures
local server readiness, rather than treating a provider API outage as a
broken container. Authenticated stream playback needs a Jio account and is
not included in the image tests.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| GHCR pull denied | Check the image name/tag and network connectivity. No token is required; if stale saved credentials cause a failure, retry with a separate empty `DOCKER_CONFIG` directory. |
| Port 5002 already in use | Choose another host port or complete the deliberate native-service migration. |
| Certificate warning | Trust the local certificate on the client, or supply an appropriate trusted certificate pair in `/tls`. |
| Health check fails after address change | Certificate must include localhost/127.0.0.1 for health checks; renew it with the required SANs. |
| EPG missing immediately after startup | Allow initial generation; check `docker compose logs` and upstream connectivity. |
| Tamil HD channels missing | Remove `sub=hide`, then update the TiviMate playlist. |
| Playlist loads but a channel fails | Check account entitlement, Jio login, DRM/device support, and playback in the web interface. |
| Scheduled image build fails | Read the repository's Actions run; the existing deployed container keeps running. |

## Attribution and references

- [JioTV Go upstream](https://github.com/JioTV-Go/jiotv_go)
- [Upstream release v3.22.0](https://github.com/JioTV-Go/jiotv_go/releases/tag/v3.22.0)
- [Upstream IPTV guide](https://github.com/JioTV-Go/jiotv_go/blob/v3.22.0/docs/usage/iptv.md)
- [Publishing Docker images in GitHub Actions](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [GitHub Container Registry permissions and authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

The unmodified upstream executable and its license are included with attribution;
see `NOTICE.md` and `LICENSE.upstream`.
