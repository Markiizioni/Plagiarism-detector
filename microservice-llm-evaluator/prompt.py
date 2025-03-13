def generate_plagiarism_prompt(code: str) -> str:
   return f"""
You are a plagiarism detection assistant. 

Given the following code snippet, determine whether it is plagiarized. 
Respond strictly with only one word: "Yes" if the code is plagiarized, or "No" if it's not.

Code snippet:
\"\"\"
{code}
\"\"\"

Your answer:
"""