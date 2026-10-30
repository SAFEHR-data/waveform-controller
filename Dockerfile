FROM python:3.13.18-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS waveform_base
LABEL authors="Stephen Thompson, Jeremy Stein"
# Cron is really small. For the sake of not having to reinstall it all the time,
# put it on both images even though we only need it on exporter.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
      cron \
      libgssapi-krb5-2 \
      libkrb5-3 \
      libltdl7 && \
    apt-get autoremove --yes && apt-get clean --yes && rm -rf /var/lib/apt/lists/*
# uv image label "0.13.6"
COPY --from=ghcr.io/astral-sh/uv@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /uvx /bin/
ARG UVCACHE=/root/.cache/uv
COPY PIXL /PIXL
WORKDIR /app
COPY waveform-controller/pyproject.toml waveform-controller/uv.lock /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
COPY waveform-controller/. /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
# Optional: only for integration-test image builds (compose/build-arg INSTALL_COVERAGE=1).
# Editable install so imports resolve under /app/src (matches source=["src"] for coverage).
# coverage.py is inert unless COVERAGE_PROCESS_START is set.
ARG INSTALL_COVERAGE=0
RUN --mount=type=cache,target=${UVCACHE} \
    if [ "$INSTALL_COVERAGE" = "1" ]; then \
      uv pip install --system -e '.[coverage]'; \
    fi
FROM waveform_base AS waveform_controller
CMD ["emap-extract-waveform"]
FROM waveform_base AS waveform_exporter
ENTRYPOINT ["/app/exporter-scripts/entrypoint.sh"]
