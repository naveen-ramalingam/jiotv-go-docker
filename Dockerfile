FROM alpine:3.24.3 AS fetch
ARG TARGETARCH
RUN apk add --no-cache ca-certificates python3
WORKDIR /build
COPY upstream.lock.json ./
COPY scripts/fetch_binary.py scripts/release_utils.py ./scripts/
RUN python3 scripts/fetch_binary.py --arch "${TARGETARCH}" --output /out/jiotv_go

FROM alpine:3.24.3
ARG PACKAGE_VERSION=1.0.1
ARG UPSTREAM_VERSION=v3.22.0
LABEL org.opencontainers.image.title="JioTV Go Docker packaging" \
      org.opencontainers.image.source="https://github.com/naveen-ramalingam/jiotv-go-docker" \
      org.opencontainers.image.version="${PACKAGE_VERSION}" \
      org.opencontainers.image.licenses="CC-BY-4.0" \
      io.jiotv-go.upstream.version="${UPSTREAM_VERSION}"
RUN apk add --no-cache ca-certificates curl openssl su-exec tzdata \
    && addgroup -S -g 10001 jiotv \
    && adduser -S -D -H -u 10001 -G jiotv -h /data -s /sbin/nologin jiotv \
    && mkdir -p /data /tls /etc/jiotv-go /usr/share/licenses/jiotv-go /usr/share/jiotv-go
COPY --from=fetch /out/jiotv_go /usr/local/bin/jiotv_go
COPY docker/entrypoint.sh docker/healthcheck.sh /usr/local/bin/
COPY docker/config.toml /etc/jiotv-go/config.toml
COPY LICENSE.upstream NOTICE.md /usr/share/licenses/jiotv-go/
COPY upstream.lock.json /usr/share/jiotv-go/upstream.lock.json
RUN chmod 0755 /usr/local/bin/jiotv_go /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh
ENV TZ=Asia/Kolkata \
    JIOTV_PATH_PREFIX=/data \
    JIOTV_LOG_PATH=/data/logs \
    JIOTV_LOG_TO_STDOUT=true \
    JIOTV_EPG=true \
    JIOTV_DRM=true \
    JIOTV_TLS_NAMES=localhost,127.0.0.1
WORKDIR /data
VOLUME ["/data", "/tls"]
EXPOSE 5002
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 CMD ["/usr/local/bin/healthcheck.sh"]
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["serve"]
