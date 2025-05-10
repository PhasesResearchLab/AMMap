FROM continuumio/miniconda3

RUN apt-get update \
    && apt-get install -y gcc \
    && conda install -y -c conda-forge "nim>2" \
    && conda install -y -c conda-forge python=3.11 liblapack jupyter numpy pandas plotly scikit-learn \
    && nimble install -y arraymancer nimpy \
    && pip install pqam-rmsadtandoc2023 pathfinding \
    && pip install git+https://github.com/HUISUN24/scheil.git \
    && pip install pycalphad==0.10.5

WORKDIR /workspace
