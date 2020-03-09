FROM ubuntu:latest

RUN apt-get update -y && \
    apt-get install -y build-essential git golang-go go-dep

ENV GOPATH=/usr/src/go
ENV PATH=$PATH:$GOPATH/bin

COPY . $GOPATH/src/github.com/ohsu-comp-bio/funnel
WORKDIR $GOPATH/src/github.com/ohsu-comp-bio/funnel
RUN make

VOLUME /opt/funnel/funnel-work-dir
EXPOSE 8000 9090
ENTRYPOINT ["/usr/src/go/bin/funnel"]
