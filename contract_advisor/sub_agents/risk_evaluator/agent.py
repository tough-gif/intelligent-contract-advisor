"""Risk Evaluator Agent Implementation with Parallel Category Validation"""

import asyncio
import json
import logging
from google.cloud import storage
from google.adk.agents import Agent
from google.genai import Client, types
from ...config import config
from . import prompts

logger = logging.getLogger(__name__)

class ParallelRiskEvaluatorAgent(Agent):
    """
    Evaluates contracts for strategic risks against multiple rule categories in parallel.
    """
    def __init__(self, name="RiskEvaluatorAgent", description="Evaluates contracts for risks using a multi-category rulebook."):
        super().__init__(name=name, description=description)
        self.output_key = "risk_evaluation"

    async def run(self, invocation_context):
        """
        Executes the parallel evaluation logic.
        """
        state = invocation_context.state
        logger.info("--- [START] Parallel Risk Evaluation ---")

        # 1. Load rulebook configuration and files
        rule_files = self._load_rulebook_config()
        if not rule_files:
            logger.error("No rule files identified for evaluation.")
            state[self.output_key] = "ERROR: No rule files found in configuration or bucket."
            return state[self.output_key]

        logger.info(f"Identified {len(rule_files)} rule categories to evaluate.")

        rules = self._load_rule_files(rule_files)
        if not rules:
            logger.error("Failed to load rule contents from GCS.")
            state[self.output_key] = "ERROR: Could not load any rule files from GCS."
            return state[self.output_key]

        # 2. Prepare inputs
        contract_text = state.get("current_contract_text", "[NO CONTRACT LOADED IN CONTEXT]")
        extracted_terms = state.get("extracted_terms", "[NO TERMS EXTRACTED YET]")
        
        if contract_text == "[NO CONTRACT LOADED IN CONTEXT]":
            logger.warning("Aborting evaluation: No contract text found in state.")
            state[self.output_key] = "ERROR: No contract loaded. Cannot evaluate risks."
            return state[self.output_key]

        # 3. Execute Parallel Evaluation
        logger.info("Initializing Gemini client for parallel calls...")
        genai_client = Client(
            project=config.project_id,
            location=config.location
        )

        eval_tasks = []
        rule_list = list(rules.items())
        
        for i, (file_name, content) in enumerate(rule_list):
            logger.info(f"[{i+1}/{len(rule_list)}] Scheduling evaluation for: {file_name}")
            eval_tasks.append(
                self._evaluate_single_rule(genai_client, file_name, content, contract_text, extracted_terms)
            )

        # Run all evaluations concurrently using the async client
        eval_results = await asyncio.gather(*eval_tasks)
        logger.info("All parallel evaluations completed.")

        # 4. Merge results for the final state
        header = "Based on the provided contract text and the playbook requirements, here's an evaluation of the risks:\n\n### Risk Evaluation Summary:\n\n"
        merged_findings = ""
        risk_count = 1
        
        for result in eval_results:
            clean_result = result.strip()
            if clean_result and "[NO DEVIATIONS FOUND]" not in clean_result and "ERROR" not in clean_result:
                merged_findings += f"{risk_count}. {clean_result}\n\n"
                risk_count += 1
        
        if not merged_findings:
            final_evaluation = f"{header}No deviations from the Corporate Legal Playbook were identified."
        else:
            final_evaluation = f"{header}{merged_findings}"

        state[self.output_key] = final_evaluation.strip()

        logger.info("--- [END] Parallel Risk Evaluation ---")
        return final_evaluation

    def _load_rulebook_config(self):
        """Reads rule_config.json from the rule bucket or falls back to listing all .md files."""
        if not config.rulebook_bucket_name:
            logger.error("RULEBOOK_BUCKET_NAME is not configured.")
            return []
        
        try:
            client = storage.Client(project=config.project_id)
            bucket = client.bucket(config.rulebook_bucket_name)
            blob = bucket.blob("rule_config.json")
            
            if blob.exists():
                logger.info("Found rule_config.json in rule bucket.")
                data = json.loads(blob.download_as_text())
                return data.get("rule_files", [])
            
            # Fallback: list all .md and .txt files
            logger.info("rule_config.json not found. Listing all .md files in bucket as fallback.")
            blobs = client.list_blobs(config.rulebook_bucket_name)
            return [b.name for b in blobs if b.name.endswith((".md", ".txt")) and b.name != "rule_config.json"]
        except Exception as e:
            logger.error(f"Error loading rulebook configuration: {e}")
            return []

    def _load_rule_files(self, rule_files):
        """Loads the content of each rule file from GCS."""
        client = storage.Client(project=config.project_id)
        bucket = client.bucket(config.rulebook_bucket_name)
        rules = {}
        for f in rule_files:
            try:
                blob = bucket.blob(f)
                if blob.exists():
                    rules[f] = blob.download_as_text()
                else:
                    logger.warning(f"Rule file '{f}' listed in config but not found in bucket.")
            except Exception as e:
                logger.error(f"Failed to load rule file '{f}': {e}")
        return rules

    async def _evaluate_single_rule(self, client, category, rule_content, contract_text, extracted_terms):
        """Performs a single LLM call for a specific rule category using the async client."""
        prompt = prompts.RISK_EVALUATOR_PROMPT.format(
            extracted_terms=extracted_terms,
            current_contract_text=contract_text,
            corporate_playbook=rule_content
        )
        
        try:
            # Use the async client (client.aio) for true parallelism
            response = await client.aio.models.generate_content(
                model=config.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=config.temperature,
                    top_p=config.top_p,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM Error for category '{category}': {e}")
            return f"ERROR evaluating category '{category}': {e}"

# Instantiate the agent for use in the pipeline
risk_evaluator_agent = ParallelRiskEvaluatorAgent()
