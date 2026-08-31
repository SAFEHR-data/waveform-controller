FROM python:3.13-slim-bookworm@sha256:8092ae2ef67061f9db412458dbdce44dbf16748fb3cae5cdbd020f467a9712d0
LABEL authors="Stephen Thompson, Jeremy Stein"

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends ca-certificates curl && \
    apt-get autoremove --yes && apt-get clean --yes && rm -rf /var/lib/apt/lists/*

# Not in apt and no official docker image, so install supercronic from: https://github.com/aptible/supercronic/releases
ARG SUPERCRONIC_VERSION=v0.2.49
ARG TARGETARCH
# don't use SHA1 as per instructions as it's insecure
RUN case "${TARGETARCH}" in \
    amd64) SUPERCRONIC_SHA256SUM=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1 ;; \
    arm64) SUPERCRONIC_SHA256SUM=02aa0cb229ba09050cba6638059dadb9eedc2276632ea43d6a57a2f8c1629dd5 ;; \
    *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && SUPERCRONIC=supercronic-linux-${TARGETARCH} \
    && SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/${SUPERCRONIC} \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA256SUM}  ${SUPERCRONIC}" | sha256sum --check - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# uv image label "0.12.5"
COPY --from=ghcr.io/astral-sh/uv@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /uvx /bin/

ARG UVCACHE=/root/.cache/uv
WORKDIR /app

COPY monitoring/monitor.py monitoring/monitor.py.lock /app/
RUN uv lock --check --script monitor.py

RUN --mount=type=cache,target=${UVCACHE} uv export --script monitor.py --locked | uv pip install --system -r -

COPY monitoring/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
