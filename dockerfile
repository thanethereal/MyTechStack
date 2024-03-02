FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update --fix-missing
RUN apt-get install -y python3 python3-pip git nano ffmpeg libsm6 libxext6 \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

ARG env_state
ENV ENV_STATE=${env_state:-dev}

ARG app_home
ENV APP_HOME=${app_home:-/app}

RUN echo "ENV_STATE=$ENV_STATE APP_HOME=$APP_HOME"

WORKDIR ${APP_HOME}
COPY . $APP_HOME

RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENTRYPOINT [ "/bin/bash" ]

CMD [ "start.sh" ]