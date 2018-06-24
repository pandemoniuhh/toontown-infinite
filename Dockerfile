FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
                        python2.7 \
                        python-pip \
                        libfreetype6 \
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
