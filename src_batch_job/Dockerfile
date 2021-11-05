FROM continuumio/miniconda3

# Update the system
RUN apt-get update && apt-get install -y

# Copy content of this dir to the docker image
COPY . /app
WORKDIR /app

# Create the conda environment
RUN conda env create -f environment.yaml

# Set OMP_NUM_THREADS variable as the number of vCPUs divided by two.
# Number of vCPUs defined in the CDK python code.
ENV OMP_NUM_THREADS "4"
ENV KMP_AFFINITY "granularity=fine,compact,1,0"

# Run the batch job
ENTRYPOINT ["conda", "run", "-n", "batch-docker-conda", "python", "main.py"]
