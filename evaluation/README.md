# Plagiarism Detection Evaluation Tool

This Docker-based tool evaluates three different plagiarism detection approaches and generates comprehensive reports and visualizations.

## Features

- Evaluates three plagiarism detection methods:
  - Combined approach
  - LLM-only approach
  - Threshold approach
- Generates detailed CSV reports with per-test-case results
- Creates summary metrics in CSV format
- Produces visualizations: 
  - Confusion matrices for each method
  - Comparative bar chart of key metrics

## Setup

1. Create the following directory structure:
   ```
   plagiarism-evaluator/
   ├── data/
   │   └── test_cases.jsonl
   ├── results/
   ├── Dockerfile
   ├── docker-compose.yml
   ├── plagiarism_evaluator.py
   └── requirements.txt
   ```

2. Place your test cases in `data/test_cases.jsonl` in the format:
   ```json
   {"code": "your code here", "expected": true}
   ```

3. Make sure your API endpoints are accessible from the Docker container. By default, the system uses:
   - Combined approach: http://host.docker.internal:8001/check-plagiarism
   - LLM-only approach: http://host.docker.internal:8002/check
   - Threshold approach: http://host.docker.internal:8003/search-similar

## Usage

### Using Docker Compose (recommended)

```bash
# Build and run the container
docker-compose up --build

# To specify custom API endpoints
COMBINED_API_URL=http://your-endpoint:port/path \
LLM_API_URL=http://your-endpoint:port/path \
THRESHOLD_API_URL=http://your-endpoint:port/path \
docker-compose up
```

### Using Docker directly

```bash
# Build the image
docker build -t plagiarism-evaluator .

# Run the container
docker run -v $(pwd)/data:/data -v $(pwd)/results:/results plagiarism-evaluator
```

### Customizing Parameters

You can customize the evaluation parameters by passing arguments to the Docker container:

```bash
docker run -v $(pwd)/data:/data -v $(pwd)/results:/results plagiarism-evaluator \
  --test-file /data/my_test_file.jsonl \
  --combined-api http://your-combined-api:port/path \
  --llm-api http://your-llm-api:port/path \
  --threshold-api http://your-threshold-api:port/path \
  --output-dir /results
```

## Output

The tool generates the following outputs in the `results/` directory:

1. `detailed_results_TIMESTAMP.csv` - Contains detailed results for each test case and method
2. `metrics_summary_TIMESTAMP.csv` - Contains summary metrics for each method
3. Confusion matrix visualizations for each method
4. A comparative visualization of key metrics across all methods

## Troubleshooting

### API Connectivity Issues

- On Linux hosts, you may need to uncomment the `extra_hosts` section in `docker-compose.yml` to enable access to the host machine.
- Ensure your API services are running and accessible from within the Docker container.
- Check network settings if you're running the APIs in other containers.

### Missing Dependencies

If you need additional Python dependencies:

1. Add them to `requirements.txt`
2. Rebuild the Docker image: `docker-compose build` or `docker build -t plagiarism-evaluator .`