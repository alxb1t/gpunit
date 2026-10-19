# The image every row of `gpunit/serve/models.toml` serves on: vLLM, sshd, and boot.py from this tree.
# Why: decision D40. Build from the repository root: docker buildx build -f serve/Dockerfile .
FROM vllm/vllm-openai:v0.31.0@sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3

# ca-certificates: boot.py's stop calls RunPod over TLS. The host keys go: boot.py makes the pod's own.
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server ca-certificates \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_*
ENV DO_NOT_TRACK=1 HF_HUB_DISABLE_TELEMETRY=1 VLLM_NO_USAGE_STATS=1
COPY boot/boot.py /opt/gpunit/boot.py
ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]
COPY serve/launch.py /opt/gpunit/launch.py
CMD ["python3", "/opt/gpunit/launch.py"]
