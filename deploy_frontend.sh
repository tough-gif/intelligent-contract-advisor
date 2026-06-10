#!/bin/bash

# Load configuration from .env file
if [ -f .env ]; then
    echo "Loading configuration from .env..."
    while IFS= read -r line || [ -n "$line" ]; do
        # Ignore comments and empty lines
        if [[ ! "$line" =~ ^# ]] && [[ ! -z "$line" ]]; then
            # Remove quotes and export
            clean_line=$(echo "$line" | sed 's/"//g' | sed "s/'//g")
            export "$clean_line"
        fi
    done < .env
else
    echo "ERROR: .env file not found."
    exit 1
fi

# Map env vars
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
REGION=$GOOGLE_CLOUD_LOCATION
# AGENT_RESOURCE_ID is already exported from .env

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$AGENT_RESOURCE_ID" ]; then
    echo "ERROR: Missing required configuration in .env file."
    echo "Required: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, AGENT_RESOURCE_ID"
    exit 1
fi

IMAGE_TAG="$REGION-docker.pkg.dev/$PROJECT_ID/contract-advisor-repo/gradio-app:latest"

echo "Deploying Cloud Run service..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Agent Resource ID: $AGENT_RESOURCE_ID"
echo "Image: $IMAGE_TAG"

gcloud run deploy contract-advisor-frontend \
    --image="$IMAGE_TAG" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --memory=1Gi \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,AGENT_RESOURCE_ID=$AGENT_RESOURCE_ID" \
    --project="$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo "Deployment successful!"
else
    echo "Deployment failed."
fi
