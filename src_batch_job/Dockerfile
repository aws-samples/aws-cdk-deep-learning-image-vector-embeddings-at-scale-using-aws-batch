From nvidia/cuda:11.0.3-cudnn8-runtime-ubuntu20.04

ARG GITLAB_TOKENID
ARG GITLAB_TOKEN

WORKDIR /app/
COPY . /app/

RUN apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common \
    libsm6 libxext6 libxrender-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN echo "**** Installing Python ****" && \
    add-apt-repository ppa:deadsnakes/ppa &&  \
    apt-get install -y build-essential git python3.8 python3.8-dev python3-pip && \
    curl -O https://bootstrap.pypa.io/get-pip.py && \
    python3.8 get-pip.py && \
    rm -rf /var/lib/apt/lists/*

RUN pip3.8 install -r requirements.txt \
    git+https://$GITLAB_TOKENID:$GITLAB_TOKEN@gitlab.aws.dev/autogluon-team/automl_multimodal_benchmark.git@master#auto_mm_bench

# Run the batch job
ENTRYPOINT ["./entrypoint.sh"]
