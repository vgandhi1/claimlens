# CLaimLens — standalone demo image.
#
# The trained model (models/anomaly_clf.joblib) is a BUILD ARTIFACT and is
# never committed (regenerated via evaluate.py). This image therefore
# generates sample data and trains the model AT BUILD TIME so it is baked
# into the layer, then serves the FastAPI app at runtime — no external
# model file or volume required.

FROM python:3.12-slim

WORKDIR /app

# claimlens/ is imported as a top-level package by the build scripts and the
# app; /app must be on the import path at build and runtime (pyproject's
# pythonpath only applies to pytest).
ENV PYTHONPATH=/app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code needed at build + run (pyproject sets pythonpath=["."]).
COPY claimlens/ ./claimlens/
COPY data/ ./data/
COPY evaluate.py ./
COPY pyproject.toml ./

# Build-time model generation: sample data -> train -> models/*.
RUN python data/generate_sample_data.py && python evaluate.py

ENV ENVIRONMENT=development
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "claimlens.api:app", "--host", "0.0.0.0", "--port", "8001"]
