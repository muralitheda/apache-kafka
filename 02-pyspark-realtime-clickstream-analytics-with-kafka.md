## PySpark Structured Streaming program that reads a clickstream from a Kafka topic and prints a result to the console.

### Prerequisites (Configuration)

1. Before running the code, you must ensure your PySpark setup can find the Kafka integration libraries.

2. Create a Highly Replicated Topic (Replication=3) 🛡️

#Create `clickstream_events` with a replication factor equal to the cluster size (3) & partition size (3).

kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 3 --partitions 3 --topic clickstream_events
kafka-topics.sh --list --zookeeper localhost:2181

#`Producer`
kafka-console-producer.sh --broker-list localhost:9092,localhost:9093,localhost:9094 --topic clickstream_events
{"user_id": 1001, "timestamp": "2025-12-14T09:25:01", "page_url": "/home", "action": "view", "duration_ms": 1200}
{"user_id": 1002, "timestamp": "2025-12-14T09:25:15", "page_url": "/product/shirt-x", "action": "view", "duration_ms": 3500}
{"user_id": 1001, "timestamp": "2025-12-14T09:25:20", "page_url": "/product/shirt-x", "action": "click", "duration_ms": 0}
{"user_id": 1003, "timestamp": "2025-12-14T09:25:25", "page_url": "/search?q=shoes", "action": "click", "duration_ms": 0}
{"user_id": 1001, "timestamp": "2025-12-14T09:25:35", "page_url": "/add-to-cart", "action": "click", "duration_ms": 0}

#`Consumer`
kafka-console-consumer.sh --bootstrap-server localhost:9092,localhost:9093,localhost:9094 --topic clickstream_events --from-beginning

#[hduser@localhost tmp]$ `ls -ltr /tmp/kafka-logs*/clickstream*/*.log`
-rw-r--r--. 1 hduser hduser 156 Dec 14 09:27 /tmp/kafka-logs-2/clickstream_events-0/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 156 Dec 14 09:27 /tmp/kafka-logs/clickstream_events-0/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 156 Dec 14 09:27 /tmp/kafka-logs-1/clickstream_events-0/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 302 Dec 14 09:27 /tmp/kafka-logs-1/clickstream_events-2/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 302 Dec 14 09:27 /tmp/kafka-logs/clickstream_events-2/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 302 Dec 14 09:27 /tmp/kafka-logs-2/clickstream_events-2/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 310 Dec 14 09:27 /tmp/kafka-logs/clickstream_events-1/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 310 Dec 14 09:27 /tmp/kafka-logs-2/clickstream_events-1/00000000000000000000.log
-rw-r--r--. 1 hduser hduser 310 Dec 14 09:27 /tmp/kafka-logs-1/clickstream_events-1/00000000000000000000.log


# Note: MESSAGES will be posted in ROUND ROBIN order to the PARTITIONS.

3. When you run the script using `spark-submit`, you need to include the Kafka and Spark-SQL-Kafka package coordinates using the `--packages` flag:

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  streaming_kafka_clickstream.py \
  # Replace 3.5.0 with your actual Spark version if different
  # Replace 2.12 with your Scala version if different
```

### PySpark Structured Streaming Code (`streaming_kafka_clickstream.py`)

This program will connect to Kafka, read the raw data, deserialize the JSON data in the `value` column, and then calculate a rolling count of clicks per user.

```python
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
query = click_counts_df.writeStream\
    .format("console")\
    .option("truncate","false")\
    .trigger(processingTime="5 seconds")\
    .outputMode("complete")\ 
    .start()

print(f"Streaming query started on topic: {KAFKA_TOPIC}. Press Ctrl+C to stop.")

# Wait for the termination of the query
query.awaitTermination()
```

### Expected Console Output

When you run this and send data to your Kafka topic (e.g., using a Kafka producer script), the console will print a new batch every 5 seconds, showing the updated count of clicks for each user:

```
-------------------------------------------
Batch: 0
-------------------------------------------
+-------+------------+-------------------------------+
|user_id|total_clicks|processing_time                |
+-------+------------+-------------------------------+
|1001   |1           |2025-12-14 07:45:00.123        |
+-------+------------+-------------------------------+

-------------------------------------------
Batch: 1
-------------------------------------------
+-------+------------+-------------------------------+
|user_id|total_clicks|processing_time                |
+-------+------------+-------------------------------+
|1001   |1           |2025-12-14 07:45:05.543        |
|1005   |2           |2025-12-14 07:45:05.543        |
+-------+------------+-------------------------------+
```