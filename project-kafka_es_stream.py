"""
author: muralitheda

submit:
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.elasticsearch:elasticsearch-spark-30_2.12:7.12.0 /home/hduser/apache-kafka/project-kafka_es_stream.py

payload:
{
  "results": [
    {
      "gender": "male",
      "name": {
        "title": "Mr",
        "first": "Jonathan",
        "last": "Sørensen"
      },
      "location": {
        "street": {
          "number": 8054,
          "name": "Porsevej"
        },
        "city": "Rønnede",
        "state": "Sjælland",
        "country": "Denmark",
        "postcode": 35279,
        "coordinates": {
          "latitude": "-41.8937",
          "longitude": "-170.8907"
        },
        "timezone": {
          "offset": "+5:30",
          "description": "Bombay, Calcutta, Madras, New Delhi"
        }
      },
      "email": "jonathan.sorensen@example.com",
      "login": {
        "uuid": "7ebcabb4-ecc0-498e-badc-51053cfd1e97",
        "username": "smallrabbit411",
        "password": "nina",
        "salt": "4XVcJF4C",
        "md5": "0bc848a235bddf1d026bb5bbfe86e1ab",
        "sha1": "aa39d766b1ed6302450dd07b2792877291a5e575",
        "sha256": "c65fdd9e80f33e265815a3eec86cb1db9ac7ecd07bb8b402ea2ec426425aa1c6"
      },
      "dob": {
        "date": "1948-10-26T11:10:11.796Z",
        "age": 77
      },
      "registered": {
        "date": "2002-11-07T19:58:28.018Z",
        "age": 23
      },
      "phone": "27981954",
      "cell": "12101243",
      "id": {
        "name": "CPR",
        "value": "261048-7646"
      },
      "picture": {
        "large": "https://randomuser.me/api/portraits/men/31.jpg",
        "medium": "https://randomuser.me/api/portraits/med/men/31.jpg",
        "thumbnail": "https://randomuser.me/api/portraits/thumb/men/31.jpg"
      },
      "nat": "DK"
    }
  ],
  "info": {
    "seed": "d7e4f4ce2a157b6c",
    "results": 1,
    "page": 1,
    "version": "1.4"
  }
}

"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode
from pyspark.sql.types import StructType, ArrayType, StringType, MapType

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "clickstream_userapi"
ELASTICSEARCH_NODES = "localhost"
ELASTICSEARCH_PORT = "9200"
ES_INDEX_NAME = "clickstream_userapi_index/random_user" # Index/Type to write data
CHECKPOINT_LOCATION = "/tmp/spark/checkpoints/user_data" # Must be unique and persistent

# --- Define Schema for the Input Payload (CRITICAL FIXES HERE) ---

# Schema for the 'name' object: {"title":"Mr", "first":"Jonathan", "last":"Sørensen"}
name_schema = StructType() \
    .add("title", StringType(), True) \
    .add("first", StringType(), True) \
    .add("last", StringType(), True)

# Schema for the 'location' object (must define nested street, coordinates, and timezone)
location_street_schema = StructType() \
    .add("number", StringType(), True) \
    .add("name", StringType(), True)

location_timezone_schema = StructType() \
    .add("offset", StringType(), True) \
    .add("description", StringType(), True)

location_schema = StructType() \
    .add("street", location_street_schema, True) \
    .add("city", StringType(), True) \
    .add("state", StringType(), True) \
    .add("country", StringType(), True) \
    .add("postcode", StringType(), True) \
    .add("timezone", location_timezone_schema, True) # <-- Corrected to allow selecting timezone.description

# Schema for a single user record (element in the 'results' array)
user_schema = StructType() \
    .add("gender", StringType(), True) \
    .add("name", name_schema, True)   \
    .add("location", location_schema, True)\
    .add("email", StringType(), True) \
    .add("phone", StringType(), True) \
    .add("nat", StringType(), True) \
    .add("login", MapType(StringType(), StringType()), True) \
    .add("dob", MapType(StringType(), StringType()), True) \
    .add("registered", MapType(StringType(), StringType()), True) \
    .add("id", MapType(StringType(), StringType()), True) \
    .add("picture", MapType(StringType(), StringType()), True)

# Overall JSON structure containing the 'results' array and 'info' object
payload_schema = StructType() \
    .add("results", ArrayType(user_schema), True) \
    .add("info", MapType(StringType(), StringType()), True)


# --- 1. Create SparkSession ---
spark = SparkSession.builder \
    .appName("KafkaToElasticsearchStream") \
    .config("spark.es.nodes", ELASTICSEARCH_NODES) \
    .config("spark.es.port", ELASTICSEARCH_PORT) \
    .config("spark.es.resource.write", ES_INDEX_NAME) \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# --- 2. Read from Kafka ---
# Read the stream of bytes from the Kafka topic
df_kafka_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

# Convert the binary 'value' column to a string
df_raw_payload = df_kafka_stream.selectExpr("CAST(value AS STRING)")

# --- 3. Transformation and Processing ---
# Parse the JSON string value into a structured DataFrame
df_parsed = df_raw_payload.select(
    from_json(col("value"), payload_schema).alias("data")
)

# Use 'explode' to flatten the 'results' array, creating a new row for each user object
df_exploded = df_parsed.select(
    explode(col("data.results")).alias("user")
)

# Select the final columns to be written to Elasticsearch
df_final = df_exploded.select(
    col("user.gender").alias("gender"),
    col("user.email").alias("email"),
    col("user.nat").alias("nationality"),
    col("user.phone").alias("phone"),
    # Access nested fields (NOW CORRECTED):
    col("user.name.first").alias("first_name"),
    col("user.name.last").alias("last_name"),
    # Access deeply nested fields:
    col("user.location.timezone.description").alias("timezone_desc"),
    col("user.location.city").alias("city"),
    col("user.location.country").alias("country")
)
#

# --- 4. Write to Elasticsearch ---

print(f"Starting stream to Elasticsearch index: {ES_INDEX_NAME}...")

# Write the stream to Elasticsearch
query = df_final.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .option("es.resource", ES_INDEX_NAME) \
    .option("es.mapping.id", "email") \
    .option("checkpointLocation", CHECKPOINT_LOCATION) \
    .trigger(processingTime='5 seconds') \
    .start()

# Wait for the termination of the query
query.awaitTermination()