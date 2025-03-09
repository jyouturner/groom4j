#!/bin/sh

set -e -x

SPRING_ACTIVE_PROFILE=$1

metadata() {
  endpoint=$1
  curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/"${endpoint}"
}

ZONE=$(metadata "/instance/zone" | cut -d / -f 4)

java -jar \
  -Dspring.profiles.active="${SPRING_ACTIVE_PROFILE}" \
  -Dgoogle.cloud.project="${PROJECT}" \
  -Dgoogle.cloud.region="${REGION}" \
  -Dgoogle.cloud.zone="${ZONE}" \
  -Djavax.net.ssl.trustStorePassword=changeit \
  -Djavax.net.ssl.trustStore=/etc/homedepot/certs/tls-truststore.jks \
  -Dcom.sun.management.jmxremote \
  -Dcom.sun.management.jmxremote.port=9010 \
  -Dcom.sun.management.jmxremote.ssl=false \
  -Dcom.sun.management.jmxremote.authenticate=false \
  -Xms2048M \
  -Xmx2048M \
  -XX:+UseConcMarkSweepGC \
  -XX:+CMSParallelRemarkEnabled \
  -XX:+UseCMSInitiatingOccupancyOnly \
  -XX:CMSInitiatingOccupancyFraction=70 \
  -XX:+ScavengeBeforeFullGC \
  -XX:+CMSScavengeBeforeRemark \
  -XX:+CMSIncrementalMode \
  -XX:+CMSIncrementalPacing \
  -XX:NewRatio=6 \
  -XX:NewSize=768m \
  -XX:MaxNewSize=768 \
  -Dvault.tokenRenewScale=10.0 \
  -Dvault.secretRenewScale=10.0 \
  *.jar >>/var/log/orangetree-output.log 2>&1
