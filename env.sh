APP_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export SRC_DIR="$APP_HOME/src"
export AI_DIR="$APP_HOME/ai"
export LOCAL_CONFIG="$SRC_DIR/config/default.yaml"

#POSTGRESQL
export POSTGRES_USER=vmthan
export POSTGRES_PASSWORD=123456
export POSTGRES_DB=e2e-recommendation-system
export POSTGRES_HOST='localhost'
export POSTGRES_PORT=5432