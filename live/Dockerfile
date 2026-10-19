# The image `make live` boots: plain Ubuntu, sshd, and boot.py from this tree.
# No CUDA: RunPod mounts the driver and nvidia-smi. Why: decision D6.
# Build from the repository root: docker buildx build -f live/Dockerfile .
FROM ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401

# python3 with its whole standard library: boot.py imports http.client and shutil (decision D6).
# ca-certificates: boot.py's stop calls RunPod over TLS. The host keys go: boot.py makes the pod's own.
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_*

COPY boot/boot.py /opt/gpunit/boot.py

ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]
CMD ["sleep", "infinity"]
