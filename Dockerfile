FROM ubuntu:18.04

RUN apt update
RUN apt-get -y install \
    python3 \
    python3-pip \
    python3-numpy \
    python3-matplotlib

COPY . .
