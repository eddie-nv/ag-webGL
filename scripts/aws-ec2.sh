#!/usr/bin/env bash
# AWS EC2 lifecycle for the scene-agent demo box.
#
#   ./scripts/aws-ec2.sh launch      # create keypair + SG + instance
#   ./scripts/aws-ec2.sh status      # state + public DNS
#   ./scripts/aws-ec2.sh ssh         # shell in
#   ./scripts/aws-ec2.sh tunnel      # forward localhost:3000 + :8000
#   ./scripts/aws-ec2.sh stop        # stop (EBS keeps accruing)
#   ./scripts/aws-ec2.sh start       # start a stopped instance
#   ./scripts/aws-ec2.sh terminate   # nuke instance + keypair + SG
#
# Idempotent: launch reuses an existing instance if one is already tracked.
# Persists state in .aws-instance-id at the repo root (gitignored).

set -euo pipefail

REGION="${AWS_REGION:-$(aws configure get region)}"
INSTANCE_TYPE="${SCENE_INSTANCE_TYPE:-t4g.large}"
KEY_NAME="scene-agent"
SG_NAME="scene-agent-ssh"
INSTANCE_NAME="scene-agent"
ROOT_VOL_GB=20
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
STATE_FILE="${REPO_ROOT}/.aws-instance-id"

ec2() { aws ec2 --region "$REGION" "$@"; }
log() { printf '\033[36m==>\033[0m %s\n' "$*" >&2; }
err() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

read_instance_id() {
  [ -f "$STATE_FILE" ] || err "no instance tracked. run '$0 launch' first."
  cat "$STATE_FILE"
}

current_ip() { curl -fsSL https://checkip.amazonaws.com | tr -d '\n'; }

ensure_keypair() {
  if [ -f "$KEY_PATH" ] && ec2 describe-key-pairs --key-names "$KEY_NAME" >/dev/null 2>&1; then
    log "keypair $KEY_NAME exists -> $KEY_PATH"
    return
  fi
  if ec2 describe-key-pairs --key-names "$KEY_NAME" >/dev/null 2>&1; then
    err "AWS has key '$KEY_NAME' but $KEY_PATH is missing locally. Either delete the key in AWS or copy the .pem back."
  fi
  log "creating keypair $KEY_NAME"
  mkdir -p "$(dirname "$KEY_PATH")"
  ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text > "$KEY_PATH"
  chmod 400 "$KEY_PATH"
  log "saved private key -> $KEY_PATH"
}

ensure_security_group() {
  local sg_id
  sg_id=$(ec2 describe-security-groups --group-names "$SG_NAME" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
  if [ -z "$sg_id" ] || [ "$sg_id" = "None" ]; then
    log "creating security group $SG_NAME"
    sg_id=$(ec2 create-security-group --group-name "$SG_NAME" \
              --description "scene-agent SSH from caller IP only" \
              --query 'GroupId' --output text)
  else
    log "security group $SG_NAME exists ($sg_id)"
  fi

  local my_ip="$(current_ip)/32"
  if ! ec2 describe-security-groups --group-ids "$sg_id" \
       --query "SecurityGroups[0].IpPermissions[?IpProtocol=='tcp' && FromPort==\`22\`].IpRanges[?CidrIp=='$my_ip'] | [0]" \
       --output text 2>/dev/null | grep -q "$my_ip"; then
    log "authorizing SSH from $my_ip"
    ec2 authorize-security-group-ingress --group-id "$sg_id" \
        --protocol tcp --port 22 --cidr "$my_ip" >/dev/null
  fi
  echo "$sg_id"
}

latest_ubuntu_arm64_ami() {
  ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*" \
              "Name=state,Values=available" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text
}

cmd_launch() {
  if [ -f "$STATE_FILE" ]; then
    local existing
    existing=$(cat "$STATE_FILE")
    local state
    state=$(ec2 describe-instances --instance-ids "$existing" \
              --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo "missing")
    if [ "$state" != "missing" ] && [ "$state" != "terminated" ]; then
      log "instance $existing already tracked (state=$state). use 'status', 'start', or 'terminate'."
      cmd_status
      return
    fi
    log "stale state file (instance $existing is $state); replacing"
    rm -f "$STATE_FILE"
  fi

  ensure_keypair
  local sg_id
  sg_id=$(ensure_security_group)

  local ami
  ami=$(latest_ubuntu_arm64_ami)
  log "ami: $ami (Ubuntu 22.04 arm64, latest)"

  log "launching $INSTANCE_TYPE in $REGION"
  local id
  id=$(ec2 run-instances \
        --image-id "$ami" \
        --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_NAME" \
        --security-group-ids "$sg_id" \
        --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=${ROOT_VOL_GB},VolumeType=gp3}" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}}]" \
        --query 'Instances[0].InstanceId' --output text)

  echo "$id" > "$STATE_FILE"
  log "instance id: $id (tracked in $STATE_FILE)"
  log "waiting for instance to enter 'running' state..."
  ec2 wait instance-running --instance-ids "$id"
  log "running. waiting for status checks..."
  # Status checks can lag; don't block on them by default. Flip to:
  # ec2 wait instance-status-ok --instance-ids "$id"
  cmd_status
}

cmd_status() {
  local id; id=$(read_instance_id)
  ec2 describe-instances --instance-ids "$id" --query \
    'Reservations[0].Instances[0].{state:State.Name,type:InstanceType,publicDns:PublicDnsName,publicIp:PublicIpAddress,az:Placement.AvailabilityZone}' \
    --output table
}

instance_field() {
  local id; id=$(read_instance_id)
  ec2 describe-instances --instance-ids "$id" --query "Reservations[0].Instances[0].$1" --output text
}

cmd_ssh() {
  local dns; dns=$(instance_field PublicDnsName)
  [ -z "$dns" ] || [ "$dns" = "None" ] && err "no public DNS yet (instance starting?)"
  log "ssh ubuntu@$dns"
  exec ssh -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new "ubuntu@$dns"
}

cmd_tunnel() {
  local dns; dns=$(instance_field PublicDnsName)
  [ -z "$dns" ] || [ "$dns" = "None" ] && err "no public DNS yet (instance starting?)"
  log "tunnel localhost:3000+8000 -> $dns (Ctrl-C to close)"
  exec ssh -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new -N \
       -L 3000:127.0.0.1:3000 \
       -L 8000:127.0.0.1:8000 \
       "ubuntu@$dns"
}

cmd_stop() {
  local id; id=$(read_instance_id)
  log "stopping $id"
  ec2 stop-instances --instance-ids "$id" >/dev/null
  ec2 wait instance-stopped --instance-ids "$id"
  log "stopped. EBS continues to bill (~\$0.05/day for 20GB gp3)."
}

cmd_start() {
  local id; id=$(read_instance_id)
  log "starting $id"
  ec2 start-instances --instance-ids "$id" >/dev/null
  ec2 wait instance-running --instance-ids "$id"
  cmd_status
  log "note: public DNS likely changed. re-open tunnel with: $0 tunnel"
}

cmd_terminate() {
  local id; id=$(read_instance_id)
  log "terminating $id"
  ec2 terminate-instances --instance-ids "$id" >/dev/null
  ec2 wait instance-terminated --instance-ids "$id"
  rm -f "$STATE_FILE"
  log "instance terminated. cleaning up keypair + SG (skip with KEEP_KEY=1 / KEEP_SG=1)."
  if [ -z "${KEEP_KEY:-}" ]; then
    ec2 delete-key-pair --key-name "$KEY_NAME" || true
    rm -f "$KEY_PATH"
    log "deleted keypair $KEY_NAME"
  fi
  if [ -z "${KEEP_SG:-}" ]; then
    ec2 delete-security-group --group-name "$SG_NAME" || true
    log "deleted security group $SG_NAME"
  fi
  log "all clean."
}

cmd="${1:-}"
case "$cmd" in
  launch) shift; cmd_launch "$@" ;;
  status) shift; cmd_status "$@" ;;
  ssh) shift; cmd_ssh "$@" ;;
  tunnel) shift; cmd_tunnel "$@" ;;
  stop) shift; cmd_stop "$@" ;;
  start) shift; cmd_start "$@" ;;
  terminate) shift; cmd_terminate "$@" ;;
  ""|-h|--help|help)
    cat <<EOF
Usage: $0 <command>

  launch     create keypair (if missing), security group (if missing),
             and launch ${INSTANCE_TYPE} (Ubuntu 22.04 arm64, ${ROOT_VOL_GB}GB gp3).
  status     show state, type, public DNS, public IP.
  ssh        shell into the instance.
  tunnel     forward localhost:3000 + :8000 from the instance (foreground).
  stop       stop (compute billing stops; EBS continues).
  start      start a stopped instance.
  terminate  terminate + delete keypair + delete SG.

Region:    $REGION
State:     $STATE_FILE
Key:       $KEY_PATH
EOF
    ;;
  *) err "unknown command: $cmd. run '$0 help'" ;;
esac
