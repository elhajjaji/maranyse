# Client de test : ouvre de vraies sessions Bureau à distance (xfreerdp dans un écran virtuel)
# et prend des captures d'écran des sessions et du tableau de bord.
FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb freerdp2-x11 xdotool imagemagick chromium fonts-dejavu fonts-noto-color-emoji procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*
CMD ["sleep", "infinity"]
