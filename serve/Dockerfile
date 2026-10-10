# The image every row of `gpunit/serve/models.toml` serves on: vLLM, sshd, and boot.sh from this tree.
# Why: 0005 design D7. Build from the repository root: docker buildx build -f serve/Dockerfile .
FROM vllm/vllm-openai:v0.31.0@sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3

# curl: boot.sh's stop calls RunPod with it. The host keys go: boot.sh makes the pod's own.
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server curl \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_*
ENV DO_NOT_TRACK=1 HF_HUB_DISABLE_TELEMETRY=1 VLLM_NO_USAGE_STATS=1
COPY boot/boot.sh /opt/gpunit/boot.sh
ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
# Loopback only: the laptop reaches it over the session's tunnel. vLLM reads VLLM_API_KEY itself.
CMD ["sh", "-c", "${GPUNIT_VOLUME_PATH:+export HF_HOME=\"$GPUNIT_VOLUME_PATH/huggingface\";} exec vllm serve \"$SERVE_REPO\" --revision \"$SERVE_REVISION\" --served-model-name \"$SERVE_NAME\" --host 127.0.0.1 --port 8000 $SERVE_ARGS"]
