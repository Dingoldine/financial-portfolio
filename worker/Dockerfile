FROM python:3.9

# install firefox dependencies
RUN apt-get update && \
  apt-get install --assume-yes build-essential libgtk-3-0 i965-va-driver intel-media-va-driver libaom0 libavcodec58 libavutil56 libcodec2-0.8.1  \
  libcrystalhd3 libdbus-glib-1-2 libgsm1 libigdgmm5 libmp3lame0 libogg0 libopus0 libshine3 libsnappy1v5  \
  libsoxr0 libspeex1 libswresample3 libtheora0 libtwolame0 libva-drm2 libva-x11-2 libva2 libvdpau-va-gl1 \
  libvdpau1 libvorbis0a libvorbisenc2 libvpx5 libwavpack1 libx264-155 libxcb-xfixes0 libegl-mesa0 libegl1-mesa \
  libxvidcore4 libzvbi-common libzvbi0 mesa-va-drivers mesa-vdpau-drivers va-driver-all vdpau-driver-all libpci-dev

# install firefox and geckodriver
RUN GECKODRIVER_VERSION=`curl https://github.com/mozilla/geckodriver/releases/latest | grep -Po 'v[0-9]+.[0-9]+.[0-9]+'` && \
    wget https://github.com/mozilla/geckodriver/releases/download/$GECKODRIVER_VERSION/geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz && \
    tar -zxf geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz


RUN FIREFOX_SETUP=firefox-setup.tar.bz2  && \
    apt-get purge firefox && \
    curl -0 'https://download.mozilla.org/?product=firefox-latest&os=linux64' -o $FIREFOX_SETUP -L && \
    echo $FIREFOX_SETUP && \
    tar -xjf $FIREFOX_SETUP -C /opt/ && \
    ln -s /opt/firefox/firefox /usr/bin/firefox && \
    rm $FIREFOX_SETUP

WORKDIR /app

# virtual environment
ENV VIRTUAL_ENV=/opt/venv

RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN $VIRTUAL_ENV/bin/pip install --upgrade pip

COPY ./requirements.txt /app

RUN pip install -r requirements.txt

RUN mkdir geckodriver && cd geckodriver && touch geckodriver.log && cd ..

# RUN chgrp -R 0 /usr/ && chmod -R g=u /usr/

# RUN chgrp -R 0 . && chmod -R g=u .

COPY . .

CMD ["celery", "-A", "portfolio_worker", "worker", "-c", "2","--loglevel=info", "-Q", "default,celery"]
