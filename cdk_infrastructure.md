# AWS CDK Infrastructure as Code (Python)

This file provides the AWS CDK code to deploy the agentic search solution infrastructure.

```python
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
)

class AgenticSearchInfrastructureStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new VPC or use existing one
        vpc = ec2.Vpc(
            self, "AgenticSearchVPC",
            max_azs=2,
            nat_gateways=0,  # No NAT Gateway needed for this simple setup
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ]
        )

        # Create a security group for the EC2 instance
        security_group = ec2.SecurityGroup(
            self, "AgenticSearchSG",
            vpc=vpc,
            description="Security group for Agentic Search Solution",
            allow_all_outbound=True
        )

        # Add inbound rule for SSH (restrict to your IP in production)
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "Allow SSH access from anywhere (restrict in production)"
        )

        # Create an IAM role for the EC2 instance
        role = iam.Role(
            self, "AgenticSearchEC2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        # Create an S3 bucket for input/output files
        bucket = s3.Bucket(
            self, "AgenticSearchBucket",
            removal_policy=core.RemovalPolicy.DESTROY,  # For development only, use RETAIN in production
            auto_delete_objects=True  # For development only
        )

        # Grant the EC2 role access to the S3 bucket
        bucket.grant_read_write(role)

        # User data script to set up the EC2 instance
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "apt-get update -y",
            "apt-get install -y docker.io git",
            "systemctl start docker",
            "systemctl enable docker",
            "usermod -aG docker ubuntu",
            
            # Install Docker Compose
            "curl -L \"https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose",
            "chmod +x /usr/local/bin/docker-compose",
            
            # Clone the repository (replace with your actual repo URL)
            "git clone https://github.com/yourusername/agentic-search-solution.git /home/ubuntu/agentic-search-solution",
            "chown -R ubuntu:ubuntu /home/ubuntu/agentic-search-solution",
            
            # Set up Ollama
            "docker pull ollama/ollama",
            "docker run -d --name ollama-server -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama",
            
            # Pull the LLM model (adjust model name as needed)
            "docker exec ollama-server ollama pull llama3",
            
            # Build and run the application container
            "cd /home/ubuntu/agentic-search-solution",
            "docker build -t agentic-search-app .",
            
            # Create a simple startup script
            "echo '#!/bin/bash' > /home/ubuntu/start-app.sh",
            "echo 'cd /home/ubuntu/agentic-search-solution' >> /home/ubuntu/start-app.sh",
            "echo 'docker run --rm --name agentic-app --network host agentic-search-app' >> /home/ubuntu/start-app.sh",
            "chmod +x /home/ubuntu/start-app.sh",
            "chown ubuntu:ubuntu /home/ubuntu/start-app.sh"
        )

        # Create the EC2 instance
        instance = ec2.Instance(
            self, "AgenticSearchInstance",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.large"),  # Adjust based on performance needs
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            security_group=security_group,
            role=role,
            user_data=user_data,
            key_name="your-key-pair-name"  # Replace with your key pair name
        )

        # Add EBS volume for Ollama models and data
        instance.instance.add_property_override(
            "BlockDeviceMappings", [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": 30,  # 30 GB root volume
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True
                    }
                }
            ]
        )

        # Output the instance public IP and S3 bucket name
        core.CfnOutput(
            self, "InstancePublicIP",
            value=instance.instance_public_ip,
            description="Public IP address of the EC2 instance"
        )
        
        core.CfnOutput(
            self, "S3BucketName",
            value=bucket.bucket_name,
            description="Name of the S3 bucket for input/output files"
        )

app = core.App()
AgenticSearchInfrastructureStack(app, "AgenticSearchInfrastructure")
app.synth()
```

## Deployment Instructions

1. Install AWS CDK:
```bash
npm install -g aws-cdk
```

2. Install Python dependencies:
```bash
pip install aws-cdk-lib
```

3. Bootstrap your AWS environment (if not already done):
```bash
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

4. Deploy the stack:
```bash
cdk deploy
```

5. After deployment, SSH into the EC2 instance:
```bash
ssh -i your-key-pair.pem ec2-user@<instance-public-ip>
```

6. Run the application:
```bash
./start-app.sh
```

## Notes

- Replace `your-key-pair-name` with your actual EC2 key pair name
- Adjust the instance type based on your performance requirements
- For production use, restrict SSH access to specific IP addresses
- Consider adding CloudWatch for monitoring and logging
