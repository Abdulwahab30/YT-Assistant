# Use Miniconda as the base — gives us conda package manager
# with a much smaller footprint than full Anaconda (~400MB vs ~3GB)
FROM continuumio/miniconda3:24.4.0-0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Activate the conda env automatically for all subsequent RUN / CMD instructions
    CONDA_ENV_NAME=yt-assistant \
    PATH=/opt/conda/envs/yt-assistant/bin:$PATH

# Set the working directory inside the container
WORKDIR /app

# Copy the conda environment spec first (for layer caching)
# If environment.yml doesn't change, Docker reuses this expensive layer
COPY backend/environment.yml /app/backend/environment.yml

# Create the conda environment from the spec file
# --no-default-packages keeps it clean
# clean -afy removes downloaded package tarballs after install (saves ~300MB)
RUN conda env create -f /app/backend/environment.yml && \
    conda clean -afy

# Copy the entire project into the container
COPY . /app

# Expose port 8000 (the default Uvicorn port)
EXPOSE 8000

# Set working directory to backend before starting the server
WORKDIR /app/backend

# Start the FastAPI application via Uvicorn using the conda env's Python
# The PATH env var above ensures the conda env's executables are used
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
