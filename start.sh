# Quick start script for GitHub RAG Agent
set -e
# Check if .env exists
if [ ! -f .env ]; then
    echo "No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "Created .env file"
    echo "Please edit .env and add your OPENAI_API_KEY"
    echo ""
    read -p "Press enter once you've added your API key to .env..."
fi

# Check if OPENAI_API_KEY is set
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "Error: OPENAI_API_KEY not set in .env file"
    exit 1
fi

echo "Environment configured"
echo ""
echo "Starting Docker Compose stack..."
docker compose up -d

echo "Docker containers started"
sleep 1

# Check backend health
echo "Checking backend health..."
until curl -s http://localhost:8000/health > /dev/null; do
    echo "  Waiting for backend..."
    sleep 2
done
echo "Backend is ready"
echo ""

echo ""
echo "Setup Complete"
echo ""
echo "Access the application:"
echo "  - Backend API: http://localhost:8000"
echo "  - Neo4j Browser: http://localhost:7474"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "To stop the stack: docker compose down"

