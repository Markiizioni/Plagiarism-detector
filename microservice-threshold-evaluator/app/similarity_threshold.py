import logging
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

class SimilarityAnalyzer:
    """
    Handles code similarity analysis with configurable thresholds for plagiarism detection.
    """
    
    def __init__(self, 
                 high_similarity_threshold: float = 0.85, 
                 medium_similarity_threshold: float = 0.70,
                 low_similarity_threshold: float = 0.55):
        """
        Initialize the similarity analyzer with configurable thresholds.
        
        Args:
            high_similarity_threshold: Threshold for high similarity (likely plagiarism)
            medium_similarity_threshold: Threshold for medium similarity (suspicious)
            low_similarity_threshold: Threshold for low similarity (might be coincidental)
        """
        self.high_threshold = high_similarity_threshold
        self.medium_threshold = medium_similarity_threshold
        self.low_threshold = low_similarity_threshold
        
        logger.info(f"SimilarityAnalyzer initialized with thresholds: high={high_similarity_threshold}, "
                   f"medium={medium_similarity_threshold}, low={low_similarity_threshold}")
    
    def analyze_search_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze search results and categorize them based on similarity thresholds.
        
        Args:
            results: List of search results with similarity scores
            
        Returns:
            Dict containing categorized results and analysis summary
        """
        if not results:
            return {
                "analysis": "No similar code found",
                "plagiarism_detected": False,
                "results": []
            }
        
        # Process and categorize results
        categorized_results = {
            "high_similarity": [],
            "medium_similarity": [],
            "low_similarity": []
        }
        
        for result in results:
            similarity = result.get("similarity", 0)
            
            # Add category to the result
            result_with_category = dict(result)
            
            if similarity >= self.high_threshold:
                result_with_category["category"] = "high"
                categorized_results["high_similarity"].append(result_with_category)
            elif similarity >= self.medium_threshold:
                result_with_category["category"] = "medium"
                categorized_results["medium_similarity"].append(result_with_category)
            elif similarity >= self.low_threshold:
                result_with_category["category"] = "low"
                categorized_results["low_similarity"].append(result_with_category)
        
        # Determine if plagiarism is detected
        plagiarism_detected = len(categorized_results["high_similarity"]) > 0
        suspicious = len(categorized_results["medium_similarity"]) > 0
        
        # Create analysis summary
        if plagiarism_detected:
            analysis = "Potential plagiarism detected with high similarity"
        elif suspicious:
            analysis = "Suspicious similarities found, but below high plagiarism threshold"
        elif len(categorized_results["low_similarity"]) > 0:
            analysis = "Low similarity matches found, likely coincidental"
        else:
            analysis = "No significant similar code found"
        
        # Combine all results in a flattened list, with high similarity first
        all_results = (
            categorized_results["high_similarity"] + 
            categorized_results["medium_similarity"] + 
            categorized_results["low_similarity"]
        )
        
        return {
            "analysis": analysis,
            "plagiarism_detected": plagiarism_detected,
            "suspicious": suspicious,
            "high_similarity_count": len(categorized_results["high_similarity"]),
            "medium_similarity_count": len(categorized_results["medium_similarity"]),
            "low_similarity_count": len(categorized_results["low_similarity"]),
            "results": all_results
        }
        
    def get_plagiarism_summary(self, code_path: str, similarity_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of plagiarism analysis.
        
        Args:
            code_path: Path or identifier for the analyzed code
            similarity_results: Results from analyze_search_results
            
        Returns:
            Human-readable summary
        """
        if not similarity_results.get("results"):
            return f"No similar code found for {code_path}"
        
        high_count = similarity_results.get("high_similarity_count", 0)
        medium_count = similarity_results.get("medium_similarity_count", 0)
        low_count = similarity_results.get("low_similarity_count", 0)
        
        if high_count > 0:
            summary = f"⚠️ POTENTIAL PLAGIARISM DETECTED: {code_path} has {high_count} high similarity matches"
        elif medium_count > 0:
            summary = f"⚠️ SUSPICIOUS: {code_path} has {medium_count} medium similarity matches"
        elif low_count > 0:
            summary = f"ℹ️ NOTICE: {code_path} has {low_count} low similarity matches (likely coincidental)"
        else:
            summary = f"✅ No significant similarities found for {code_path}"
        
        return summary