import os
import json
import logging
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure logging for production visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PolicyParser:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.error("GROQ_API_KEY not found in environment variables.")
            raise ValueError("Missing API Key. Please check your .env file.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"

    def extract_rules(self, policy_text: str) -> List[Dict]:
        """
        Uses Groq LLM to convert human-readable policy text 
        into structured JSON rules for the Engine.
        """
        prompt = f"""
        Analyze the following corporate AI compliance policy and extract 
        specific, measurable rules for an automated governance agent.
        
        RETURN ONLY A JSON OBJECT with a key named "rules" containing a list of objects.
        Each object MUST have:
        - id: (e.g., R001)
        - text: (The actual rule sentence)
        - category: (financial, vendor, fraud, or general)
        - threshold: (numerical value if mentioned, else null)
        - severity: (CRITICAL, HIGH, or MEDIUM)
        - action: (escalate, reject, verify, or log)

        POLICY TEXT:
        {policy_text}
        """

        try:
            logger.info("Sending request to Groq for policy extraction...")
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a specialized Compliance Architect. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            
            raw_content = chat_completion.choices[0].message.content
            response_data = json.loads(raw_content)
            
            rules = response_data.get("rules", [])
            logger.info(f"Successfully extracted {len(rules)} rules.")
            return rules

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return []

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("config", exist_ok=True)
    
    # Load the sample policy
    policy_path = "mock_data/sample_policy.txt"
    if not os.path.exists(policy_path):
        logger.error(f"Policy file not found at {policy_path}")
    else:
        with open(policy_path, "r") as f:
            content = f.read()

        try:
            parser = PolicyParser()
            extracted_rules = parser.extract_rules(content)
            
            # Save to config/policy.json
            with open("config/policy.json", "w") as f:
                json.dump({"rules": extracted_rules}, f, indent=2)
            
            logger.info("config/policy.json has been updated securely.")
            # Print only for verification
            print(json.dumps(extracted_rules, indent=2))
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")