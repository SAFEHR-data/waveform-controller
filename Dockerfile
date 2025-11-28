FROM python:3.14-slim-bookworm
LABEL authors="Stephen Thompson, Jeremy Stein"
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ARG UVCACHE=/root/.cache/uv
COPY pyproject.toml uv.lock* /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
COPY . /app/
RUN --mount=type=cache,target=${UVCACHE} uv pip install --system .
CMD ["emap-extract-waveform"]