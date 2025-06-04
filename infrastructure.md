# AWS Deployment Infrastructure Design

This document details the AWS infrastructure design for deploying the agentic e-commerce search solution, focusing on the recommended EC2-based approach where both the application and the Ollama LLM run on the same instance for simplicity.

## 1. Core Components

*   **VPC (Virtual Private Cloud):** Provides an isolated network environment.
    *   A default VPC can be used, or a new one created.
    *   Will contain public and private subnets (although for this simple setup, a public subnet might suffice if direct SSH access is needed).
*   **EC2 Instance:** A single virtual server to host both the application and Ollama.
    *   **Instance Type:** Choose based on performance needs. Consider CPU-optimized (e.g., `c5.large` or `c5.xlarge`) if the LLM is CPU-bound, or a GPU instance (e.g., `g4dn.xlarge`) if using a large model that benefits significantly from GPU acceleration. Start with a general-purpose type like `t3.large` or `m5.large` and monitor performance.
    *   **AMI (Amazon Machine Image):** A standard Linux distribution like Ubuntu Server 22.04 LTS or Amazon Linux 2.
    *   **Storage (EBS):** Sufficient EBS volume size to accommodate the OS, Docker, application code, Python dependencies, Ollama installation, and downloaded LLM models (models can be several GBs).
*   **Security Group:** Acts as a virtual firewall for the EC2 instance.
    *   **Inbound Rules:**
        *   Allow SSH (TCP port 22) from your specific IP address for management.
        *   (Optional) Allow HTTP/HTTPS (TCP ports 80/443) if you plan to add a web interface later.
        *   Ensure the instance can talk to itself on the Ollama port (TCP 11434) - typically allowed by default within the same security group.
    *   **Outbound Rules:**
        *   Allow all outbound traffic (needed for web scraping, pulling Docker images, installing packages, etc.).
*   **IAM Role (for EC2 Instance):** Grants necessary permissions to the EC2 instance.
    *   (Optional) Permissions to access S3 (e.g., `s3:PutObject`, `s3:GetObject`) if the application will read input files from or write output files to an S3 bucket.
*   **S3 Bucket (Optional but Recommended):**
    *   Store input search task files.
    *   Store output result files (JSON/CSV).
    *   Provides durable and scalable storage separate from the EC2 instance.
*   **Docker:** Containerization platform installed on the EC2 instance.
    *   **Application Container:** Runs the Python application (scraper, evaluator, orchestrator).
    *   **Ollama Container:** Runs the Ollama server (using the official `ollama/ollama` image).

## 2. Deployment Workflow (Manual Steps / To be Automated with IaC)

1.  **Provision Infrastructure:** Create VPC, EC2 instance, Security Group, IAM Role (using AWS Console, CLI, or IaC).
2.  **Configure EC2 Instance:**
    *   SSH into the instance.
    *   Install Docker and Docker Compose.
    *   Install necessary drivers (e.g., NVIDIA drivers if using a GPU instance for Ollama).
    *   Clone the application repository or copy the code (`scraper.py`, `llm_evaluator.py`, `requirements.txt`, `Dockerfile`, etc.) onto the instance.
3.  **Build Application Docker Image:** Navigate to the application code directory and run `docker build -t agentic-search-app .`.
4.  **Set up Ollama:**
    *   Pull the official Ollama Docker image: `docker pull ollama/ollama`.
    *   Pull the desired LLM model: `docker run --rm ollama/ollama ollama pull <model_name>` (e.g., `llama3`).
5.  **Run Containers:**
    *   Start the Ollama container, potentially mounting a volume for models and exposing the port: `docker run -d --name ollama-server -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama` (Add `--gpus all` if using GPU instance).
    *   Start the application container, linking it to the Ollama network or ensuring it can reach `localhost:11434`. Mount volumes for input/output if not using S3. `docker run --rm --name agentic-app --network host agentic-search-app` (Using `--network host` is simple for localhost communication, but consider creating a Docker network for better isolation).
6.  **Execute Application:** The application container should run the main orchestrator script upon startup, which reads input, performs scraping and evaluation, and writes output.

## 3. Infrastructure as Code (IaC) - AWS CDK Example Outline

Using AWS CDK with Python allows defining the infrastructure programmatically.

*   **Project Setup:** `cdk init app --language python`
*   **`app.py`:** Entry point, defines stacks.
*   **`cdk_stack.py` (or similar):**
    *   Import necessary CDK modules (`aws_ec2`, `aws_iam`, `aws_s3`).
    *   Define the VPC (or use `Vpc.from_lookup` for default).
    *   Define the Security Group with appropriate ingress/egress rules.
    *   Define the IAM Role for the EC2 instance, adding S3 policies if needed.
    *   Define the EC2 instance:
        *   Specify VPC, instance type, AMI (`ec2.MachineImage.latest_amazon_linux()` or similar).
        *   Assign the Security Group and IAM Role.
        *   Use `user_data` to script the initial setup (install Docker, Docker Compose, Git, clone repo, potentially start services - though managing services via user data can be complex).
    *   Define the S3 bucket.
    *   Output relevant information (e.g., Instance ID, S3 bucket name).

This IaC setup automates step 1 (Provision Infrastructure) and partially automates step 2 (Configure EC2 Instance). Steps 3-6 would typically still be performed manually after the infrastructure is up, or further automated using configuration management tools (Ansible, Chef, Puppet) or more complex User Data/Cloud-Init scripts.
