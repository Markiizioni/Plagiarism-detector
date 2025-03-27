import os
import logging
from typing import List, Dict, Any, Optional
import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LLMPlagiarismDetector:
    """
    Uses an LLM to detect plagiarism by analyzing similar code chunks.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 model: str = "gpt-3.5-turbo",
                 temperature: float = 0.0):
        """
        Initialize the plagiarism detector with OpenAI configuration.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: OpenAI model to use
            temperature: Temperature setting for the model (lower is more deterministic)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key not found. Please set OPENAI_API_KEY in your environment.")
        
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"LLM Plagiarism Detector initialized with model: {model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_similarity(self, 
                          query_code: str, 
                          similar_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze if the query code is plagiarized based on similar code chunks.
        
        Args:
            query_code: The code being checked for plagiarism
            similar_results: List of similar code chunks with metadata
        
        Returns:
            Analysis results including plagiarism determination
        """
        if not similar_results:
            return {
                "analysis": "No similar code found",
                "plagiarism_detected": False,
                "results": similar_results
            }
        
        # Format the similar results for LLM analysis
        formatted_results = self._format_results_for_llm(similar_results)
        
        # Generate the prompt for the LLM
        prompt = self._generate_prompt(query_code, formatted_results)
        
        try:
            # Send the prompt to the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer specializing in plagiarism detection. Your task is to analyze a query code and determine if it's plagiarized from any of the similar code chunks provided."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Process the LLM response
            analysis_result = self._process_llm_response(response.choices[0].message.content, similar_results)
            
            return analysis_result
        except Exception as e:
            logger.error(f"Error in LLM analysis: {str(e)}")
            # Fallback to a simple analysis if LLM fails
            return self._fallback_analysis(similar_results)
    
    def _format_results_for_llm(self, similar_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format the similar results for the LLM."""
        formatted_results = []
        
        for i, result in enumerate(similar_results):
            # Convert FAISS distance to similarity score (approximate)
            # FAISS L2 distance is Euclidean distance, so we normalize it to a similarity score
            distance = result.get("distance", 0)
            # This is a simple conversion - adjust based on your embedding space
            similarity_score = max(0, 1.0 - (distance / 2.0))
            
            formatted_result = {
                "id": i + 1,
                "similarity_score": similarity_score,
                "code": result.get("chunk", ""),
                "file_name": result.get("metadata", {}).get("file_name", "unknown"),
                "file_path": result.get("metadata", {}).get("file_path", "unknown")
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _generate_prompt(self, query_code: str, formatted_results: List[Dict[str, Any]]) -> str:
        """Generate the prompt for the LLM."""
        prompt = "Please analyze the following query code and determine if it's plagiarized from any of the similar code chunks provided. "
        prompt += "Consider not just exact matches but also code that has been slightly modified or refactored. "
        prompt += "Provide a comprehensive analysis considering ALL chunks together, not separate analyses per chunk.\n\n"
        
        prompt += "Query code to analyze:\n```\n" + query_code + "\n```\n\n"
        
        prompt += "Similar code chunks:\n"
        for result in formatted_results:
            prompt += f"[{result['id']}] Similarity score: {result['similarity_score']:.2f}\n"
            prompt += f"File: {result['file_name']}\n"
            prompt += "```\n" + result['code'] + "\n```\n\n"
        
        prompt += "Respond with a JSON object containing ONLY:\n"
        prompt += "1. 'plagiarism_detected': boolean indicating if plagiarism is detected\n"
        prompt += "2. 'analysis': a detailed explanation of your findings, considering ALL chunks together\n"
        prompt += "3. 'confidence': a value between 0 and 1 indicating your confidence level\n"
        
        return prompt
    
    def _process_llm_response(self, response_content: str, similar_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process the LLM response and combine with original results."""
        try:
            llm_analysis = json.loads(response_content)
            
            # Return a simplified analysis without individual assessments
            return {
                "plagiarism_detected": llm_analysis.get("plagiarism_detected", False),
                "analysis": llm_analysis.get("analysis", "Analysis not provided"),
                "confidence": llm_analysis.get("confidence", 0.0),
                "results": similar_results,  # Original results without individual explanations
                "llm_model": self.model
            }
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            return self._fallback_analysis(similar_results)
    
    def _fallback_analysis(self, similar_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Provide a fallback analysis when LLM processing fails."""
        # Check if any result has high similarity (convert distance to similarity)
        high_similarity = any(1.0 - (result.get("distance", 0) / 2) > 0.8 for result in similar_results)
        
        return {
            "plagiarism_detected": high_similarity,
            "analysis": "Fallback analysis due to LLM processing error. Based on vector similarity only.",
            "results": similar_results,
            "confidence": 0.5,
            "is_fallback": True
        }