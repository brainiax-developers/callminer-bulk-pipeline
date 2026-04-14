#!/bin/bash
# Usage
#
# ./assume_role.sh $CLIENT_ROLE_ARN $EXTERNAL_ID client
# aws s3 ls --profile client --region eu-west-1

ROLE_ARN=$1
EXTERNAL_ID=$2
OUTPUT_PROFILE=$3

echo "Assuming role $ROLE_ARN"
sts=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --external-id "$EXTERNAL_ID" \
  --role-session-name "$OUTPUT_PROFILE" \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
  --output text)
echo "Converting sts to array"
read -r -a sts <<< "$sts"
echo "AWS_ACCESS_KEY_ID is ${sts[0]}"
aws configure set aws_access_key_id "${sts[0]}" --profile "$OUTPUT_PROFILE"
aws configure set aws_secret_access_key "${sts[1]}" --profile "$OUTPUT_PROFILE"
aws configure set aws_session_token "${sts[2]}" --profile "$OUTPUT_PROFILE"
echo "credentials stored in the profile named $OUTPUT_PROFILE"
