FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
                        python2.7 \
                        python-pip \
                        build-essential \
                        pkg-config \
                        python-dev \
                        libpng-dev \
                        libjpeg-dev \
                        libtiff-dev \
                        zlib1g-dev \
                        libssl-dev \
                        libx11-dev \
                        libgl1-mesa-dev \
                        libxrandr-dev \
                        libxxf86dga-dev \
                        libxcursor-dev \
                        bison \
                        flex \
                        libfreetype6-dev \
                        libvorbis-dev \
                        libeigen3-dev \
                        libopenal-dev \
                        libode-dev \
                        libbullet-dev \
                        nvidia-cg-toolkit \
                        libgtk2.0-dev \
                   && pip install pipenv


COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

WORKDIR /server

COPY otp otp
COPY toontown toontown
COPY dclass dclass

ENV DISTRICT_NAME="Nuttyboro"
ENV MAX_CHANNELS=999999
ENV STATESERVER=4002
ENV ASTRON_IP="127.0.0.1:7100"
ENV EVENTLOGGER_IP="127.0.0.1:7198"
ENV BASE_CHANNEL=401000000

CMD python2 -m toontown.uberdog.ServiceStart --base-channel $BASE_CHANNEL \
                     --max-channels $MAX_CHANNELS --stateserver $STATESERVER \
                     --astron-ip $ASTRON_IP --eventlogger-ip $EVENTLOGGER_IP
