source env.sh

if [[ "$OSTYPE" == "msys" ]]; then
  alias python3=python
fi

#echo "Downloading weights from S3"
#
#download_weights()
# {
#    aws s3 cp s3://"$s3_bucket"/models/ "$SRC_DIR"/models/ --recursive
#}
#
#download_weights

function start() {
    python3 "$SRC_DIR"/app.py
}

start