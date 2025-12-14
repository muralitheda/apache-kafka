from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, count, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, TimestampType

# --- 1. Define the Schema for the Clickstream Data ---
# This is crucial for deserializing the JSON value from Kafka
clickstream_schema = StructType([
    StructField("user_id", IntegerType(), True),
    StructField("timestamp", TimestampType(), True), # Assume the timestamp is ISO8601 or similar
    StructField("page_url", StringType(), True),
    StructField("action", StringType(), True),
    StructField("duration_ms", LongType(), True)
])

# --- 2. Initialize Spark Session ---
# Note: Streaming applications are often run in local mode for testing
spark = SparkSession.builder \
    .appName("KafkaClickstreamStreaming") \
    .getOrCreate()

# Set log level to WARN to minimize console noise from Kafka
spark.sparkContext.setLogLevel("WARN")

# --- 3. Configuration Variables (Update these for your VM setup) ---
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"  # Your Kafka broker address
KAFKA_TOPIC = "clickstream_events"          # The name of your Kafka topic

# --- 4. Read Stream from Kafka ---
# Read data from the specified Kafka topic
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

# --- 5. Transform and Process Data ---
# Kafka data is returned with keys like 'key', 'value', 'topic', 'partition', 'offset', 'timestamp'
# The clickstream data is in the 'value' column as raw bytes/string

# a) Cast the 'value' (bytes) to STRING
string_df = kafka_df.selectExpr("CAST(value AS STRING) as json_payload", "timestamp as kafka_timestamp")

# b) Parse the JSON string using the defined schema
parsed_df = string_df.select(
    from_json(col("json_payload"), clickstream_schema).alias("data"),
    col("kafka_timestamp")
).select("data.*", "kafka_timestamp")


# c) Perform a Simple Aggregation (e.g., rolling count of clicks per user)
# We will use the 'kafka_timestamp' for processing time
click_counts_df = parsed_df.filter(col("action") == "click") \
                           .groupBy("user_id") \
                           .agg(count("*").alias("total_clicks")) \
                           .withColumn("processing_time", current_timestamp())


# --- 6. Write Stream to Console (The Action) ---
# Start the streaming query. The output will be printed to the console
# The 'complete' output mode is often used for aggregation results
query = click_counts_df.writeStream \
    .outputMode("complete") # 'complete' mode prints the entire updated result table every trigger
    .format("console")      # Sink the result to the console
    .option("truncate", "false") # Prevent truncating long strings
    .trigger(processingTime='5 seconds') # Update the result every 5 seconds
    .start()

print(f"Streaming query started on topic: {KAFKA_TOPIC}. Press Ctrl+C to stop.")

# Wait for the termination of the query
query.awaitTermination()