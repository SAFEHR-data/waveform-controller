FROM python:3.13-slim-bookworm AS waveform_base
LABEL authors="Stephen Thompson, Jeremy Stein"
# Cron is really small. For the sake of not having to reinstall it all the time,
# put it on both images even though we only need it on exporter.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends cron && \
    apt-get autoremove --yes && apt-get clean --yes && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ARG UVCACHE=/root/.cache/uv
COPY PIXL /PIXL
WORKDIR /app
COPY waveform-controller/pyproject.toml waveform-controller/uv.lock /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
COPY waveform-controller/. /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
FROM waveform_base AS waveform_controller
CMD ["emap-extract-waveform"]
FROM waveform_base AS waveform_exporter
ENTRYPOINT ["/app/exporter-scripts/entrypoint.sh"]
