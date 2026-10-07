# The image `make live` boots: plain Ubuntu, sshd, and boot.sh from this tree.
# No CUDA: RunPod mounts the driver and nvidia-smi. Why: 0001 design D14.
# Build from the repository root: docker buildx build -f live/Dockerfile .
FROM ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401

# curl: boot.sh's stop calls RunPod with it. The host keys go: boot.sh makes the pod's own.
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_*

COPY boot/boot.sh /opt/gpunit/boot.sh
RUN chmod +x /opt/gpunit/boot.sh

ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
CMD ["sleep", "infinity"]
