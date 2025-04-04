import logging
from typing import List, Dict, Any, Optional
import ast
import re

logger = logging.getLogger(__name__)

class SimilarityAnalyzer:
    def __init__(self, 
                 high_similarity_threshold: float = 0.85, 
                 medium_similarity_threshold: float = 0.70,
                 low_similarity_threshold: float = 0.55):
        # Existing initialization remains the same
        self.high_threshold = high_similarity_threshold
        self.medium_threshold = medium_similarity_threshold
        self.low_threshold = low_similarity_threshold
        
        logger.info(f"SimilarityAnalyzer initialized with thresholds: high={high_similarity_threshold}, "
                   f"medium={medium_similarity_threshold}, low={low_similarity_threshold}")
    
    def multi_dimensional_similarity_assessment(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a multi-dimensional assessment of code similarity
        
        Args:
            result: A single similarity result
        
        Returns:
            Enhanced similarity assessment
        """
        chunk = result.get('chunk', '')
        similarity = result.get('similarity', 0)
        
        return {
            "raw_similarity": similarity,
            "code_length": len(chunk),
            "structural_complexity": self._analyze_structural_complexity(chunk),
            "unique_patterns": self._count_unique_code_patterns(chunk),
            "risk_factors": self._identify_risk_factors(chunk, similarity)
        }
    
    def _analyze_structural_complexity(self, code_chunk: str) -> Dict[str, float]:
        """
        Analyze the structural complexity of the code
        
        Args:
            code_chunk: Code to analyze
        
        Returns:
            Structural complexity metrics
        """
        try:
            # Use AST to analyze code structure
            tree = ast.parse(code_chunk)
            
            # Count control flow statements
            control_flow_count = sum(
                1 for node in ast.walk(tree) 
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try))
            )
            
            # Calculate depth of nesting
            max_depth = max(
                (node.depth for node in ast.walk(tree) 
                 if hasattr(node, 'depth')), 
                default=0
            )
            
            return {
                "control_flow_complexity": min(control_flow_count / 10, 1.0),
                "nesting_depth": min(max_depth / 5, 1.0)
            }
        except Exception:
            # Fallback if AST parsing fails
            return {
                "control_flow_complexity": 0,
                "nesting_depth": 0
            }
    
    def _count_unique_code_patterns(self, code_chunk: str) -> float:
        """
        Count unique code patterns
        
        Args:
            code_chunk: Code to analyze
        
        Returns:
            Uniqueness score
        """
        # Extract unique identifiers and keywords
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code_chunk)
        unique_identifiers = len(set(identifiers))
        
        return min(unique_identifiers / 50, 1.0)
    
    def _identify_risk_factors(self, code_chunk: str, similarity: float) -> List[str]:
        """
        Identify potential plagiarism risk factors
        
        Args:
            code_chunk: Code to analyze
            similarity: Similarity score
        
        Returns:
            List of risk factors
        """
        risk_factors = []
        
        # Length-based risk
        if len(code_chunk) > 100:
            risk_factors.append("Significant code length")
        
        # Similarity-based risk
        if similarity > 0.95:
            risk_factors.append("Extremely high similarity")
        
        # Check for generic variable names
        if re.search(r'\b(temp|x|y|z|i|j|k)\b', code_chunk):
            risk_factors.append("Generic variable names")
        
        return risk_factors
    
    def enhance_similarity_analysis(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance similarity results with multi-dimensional analysis
        
        Args:
            results: Original similarity search results
        
        Returns:
            Enhanced results with additional analysis
        """
        enhanced_results = []
        for result in results:
            multi_dim_assessment = self.multi_dimensional_similarity_assessment(result)
            
            # Calculate an enhanced risk score
            risk_score = (
                0.4 * result.get('similarity', 0) + 
                0.3 * (multi_dim_assessment['code_length'] / 200) + 
                0.3 * multi_dim_assessment['structural_complexity'].get('control_flow_complexity', 0)
            )
            
            enhanced_result = {
                **result,
                "multi_dimensional_analysis": multi_dim_assessment,
                "enhanced_risk_score": risk_score,
                "is_high_risk": risk_score > 0.7
            }
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def analyze_search_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze search results and categorize them based on similarity thresholds.
        Enhance with multi-dimensional analysis.
        
        Args:
            results: List of search results with similarity scores
            
        Returns:
            Dict containing categorized results and analysis summary
        """
        if not results:
            return {
                "analysis": "No similar code found",
                "plagiarism_detected": False,
                "results": [],
                "enhanced_results": []
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
        
        # Perform multi-dimensional analysis
        enhanced_results = self.enhance_similarity_analysis(results)
        
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
            "results": all_results,
            "enhanced_results": enhanced_results
        }