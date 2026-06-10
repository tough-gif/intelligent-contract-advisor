# Intelligent Contract Advisor

The **Intelligent Contract Advisor** is an AI agent built with the **Google ADK (Agent Development Kit)** and deployed on **Vertex AI Reasoning Engine**. It automates the review of legal contracts by extracting key terms, evaluating risks against a predefined rulebook (playbook), and generating a comprehensive executive summary.

## Architecture

The system uses a hybrid architecture:
- **LeadContractAdvisor (LlmAgent):** Acts as the conversational front-end, handling user queries and routing contract review requests.
- **ContractReviewPipeline (SequentialAgent):** A deterministic four-step pipeline:
    1. **Ingestion:** Fetches and processes the document (PDF/Docx).
    2. **Term Extraction:** Identifies parties, dates, and core obligations.
    3. **Risk Evaluation:** Compares the contract against a legal playbook stored in GCS.
    4. **Critic/Summarization:** Formats the final report into a structured executive summary.

## Prerequisites

- **Python 3.12+**
- **Google Cloud Project** with Vertex AI and Cloud Storage APIs enabled.
- **[uv](https://github.com/astral-sh/uv)** for fast dependency management.
- A **GCS Bucket** to store the legal playbook (rulebook) and staging files.

## Local Setup

### 1. Install Dependencies

Using `uv`, install the project dependencies:

```bash
uv sync
```

### 2. Configure Environment

Create a `.env` file in the root directory based on the following template:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
CONTRACT_BUCKET_NAME=your-contract-bucket
RULEBOOK_BUCKET_NAME=your-rulebook-bucket
GEMINI_MODEL_NAME=gemini-2.5-flash
```

## Testing & Local Execution

You can test the agent locally using two different interfaces:

### Option A: ADK Web Interface (Recommended)
This uses the standard ADK development server:

```bash
uv run adk web
```

### Option B: Gradio UI
This uses a custom Gradio interface for advanced PDF preview and report generation:

```bash
uv run python gradio_app.py
```

## Deployment to Vertex AI

The agent can be deployed to **Vertex AI Reasoning Engine** for production use.

### 1. Build the Agent

Package the agent as a Python wheel file and output it directly to the deployment directory:

```bash
uv build --wheel --out-dir deployment
```

### 2. Deploy using the script

Use the provided deployment script to push the agent to Vertex AI:

```bash
uv run python deployment/deploy.py --create
```

## Deploying the Frontend (Gradio App) to Cloud Run

The frontend Gradio app (`gradio_app.py`) can be deployed to **Google Cloud Run**.

### Prerequisites

1.  The backend agent must already be deployed to Vertex AI Reasoning Engine (see steps above).
2.  Ensure your `.env` file is configured with the correct `AGENT_RESOURCE_ID`.
3.  **Permissions**: The default Compute Engine service account (`[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`) requires:
    *   **Storage Object Admin** (or Creator) on the `CONTRACT_BUCKET_NAME` bucket to allow users to upload files via UI.
    *   **Vertex AI User** (`roles/aiplatform.user`) to call the backend agent.

### Deployment Steps
All commands below must be executed from the root of the agent directory (`python/agents/contract-advisor5/`). 

We provide a helper script `deploy_frontend.sh` to simplify deployment.

1.  **Build and Push the Container Image:**
    Create the Artifact Registry repository and build the container image using Cloud Build:
    ```bash
    # Create repository (only needed once)
    gcloud artifacts repositories create contract-advisor-repo \
        --repository-format=docker \
        --location=us-central1 \
        --description="Docker repository for Contract Advisor" \
        --project=YOUR_PROJECT_ID

    # Build and push the image
    gcloud builds submit \
        --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/contract-advisor-repo/gradio-app:latest \
        --project=YOUR_PROJECT_ID
    ```

2.  **Deploy using the script:**
    Edit `deploy_frontend.sh` to ensure `PROJECT_ID`, `REGION`, and `AGENT_RESOURCE_ID` match your environment, then run:
    ```bash
    bash deploy_frontend.sh
    ```

    *Note: If the deployment fails at the "Setting IAM Policy" step, it means your account lacks permission to make the service public. The deployment is still successful, but the service is private. You can access it locally using:*
    ```bash
    gcloud run services proxy contract-advisor-frontend --project=YOUR_PROJECT_ID --region=us-central1
    ```

## Usage

The advisor supports two ways to access contracts:

1. **Upload a Contract:** Use either the ADK web UI or the Gradio app to upload contract files (PDF).
2. **Search/Fetch from GCS:** If a contract already exists in your `CONTRACT_BUCKET_NAME`, you can simply ask the advisor to analyze it by referencing its filename (e.g., "Analyze the contract named service_agreement_v2.pdf").

### Review Process:
- **Analysis:** The advisor will process the document through the sequential pipeline.
- **Review Results:** Once finished, the advisor provides a structured analysis. If using Gradio, you can also download a PDF version of the report.
