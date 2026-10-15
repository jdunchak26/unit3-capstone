import boto3

rds_client = boto3.client("rds", region_name="us-east-1")

response = rds_client.create_db_instance(
    DBInstanceIdentifier="bootcamp-db",
    DBInstanceClass="db.t3.micro",      
    Engine="postgres",
    MasterUsername="bootcamp_admin",    
    MasterUserPassword="admin123",
    AllocatedStorage=20,                
    MultiAZ=False,                     
    PubliclyAccessible=True,
)

print("Creating RDS instance, status:", response["DBInstance"]["DBInstanceStatus"])


waiter = rds_client.get_waiter("db_instance_available")
waiter.wait(DBInstanceIdentifier="bootcamp-db")
print("RDS instance is now available!")

description = rds_client.describe_db_instances(DBInstanceIdentifier="bootcamp-db")
endpoint = description["DBInstances"][0]["Endpoint"]["Address"]
print("Endpoint:", endpoint)