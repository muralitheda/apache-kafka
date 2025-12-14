"""
author: muralitheda
purpose: Realtime clickstream processing from Kafka to Elasticsearch

Execute:
spark-submit \
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.elasticsearch:elasticsearch-spark-30_2.12:7.12.0 \
/home/hduser/apache-kafka/streaming_kafka_clickstream_elasticsearch.py

"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, count, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, TimestampType

# ---------- Schema ----------
schema = StructType([
    StructField("user_id", IntegerType()),
    StructField("timestamp", TimestampType()),
    StructField("page_url", StringType()),
    StructField("action", StringType()),
    StructField("duration_ms", LongType())
])

# ---------- Spark Session ----------
spark = SparkSession.builder \
    .appName("KafkaToElasticsearch") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# ---------- Config ----------
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "clickstream_events"
ES_HOST = "localhost"
ES_PORT = "9200"
ES_INDEX = "clickstream_user_clicks"

# ---------- Read from Kafka ----------
kafka_df = (spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
            .option("subscribe", KAFKA_TOPIC)
            .load())

# ---------- Parse JSON ----------
parsed_df = (kafka_df
             .selectExpr("CAST(value AS STRING) AS json")
             .select(from_json(col("json"), schema).alias("d"))
             .select("d.*"))

# ---------- Aggregation ----------
result_df = (parsed_df
             .filter(col("action") == "click")
             .groupBy("user_id")
             .agg(count("*").alias("total_clicks"))
             .withColumn("processed_at", current_timestamp()))

# ---------- Write to Elasticsearch ----------
def write_to_es(df, _):
    (df.write
       .format("org.elasticsearch.spark.sql")
       .option("es.nodes", ES_HOST)
       .option("es.port", ES_PORT)
       .option("es.resource", ES_INDEX)
       .mode("append")
       .save())

query = (result_df.writeStream
         .foreachBatch(write_to_es)
         .outputMode("complete")
         .option("checkpointLocation", "/tmp/kafka_es_chk")
         .start())

query.awaitTermination()
