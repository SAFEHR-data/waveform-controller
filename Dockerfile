FROM python:3.13-slim-bookworm
LABEL authors="Stephen Thompson, Jeremy Stein"
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ARG UVCACHE=/root/.cache/uv
COPY PIXL /PIXL
WORKDIR /app
COPY waveform-controller/pyproject.toml waveform-controller/uv.lock /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
COPY waveform-controller/. /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
CMD ["emap-extract-waveform"]
