This is a detailed set of hands-on Kafka exercises covering single-broker setup, producing, consuming, and scaling up to a multi-broker cluster to test fault tolerance.

## 🛠️ Apache Kafka Hands-On Workouts

This guide covers setting up a single-broker environment, basic publishing/subscribing, scaling to a multi-broker cluster, and testing fault tolerance.

### Part 1: Single Broker Setup & Basic Operations

These steps assume a Kafka instance and Zookeeper are already running locally.

#### 1\. Create a Topic (1 Partition, 1 Replica)

Use the `kafka-topics.sh` command to create a topic named `demotopic1`.

```bash
kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 1 --partitions 1 --topic demotopic1
```

#### 2\. Verify Topic Creation

List all topics to ensure `demotopic1` appears. You can also inspect the logs directory.

```bash
kafka-topics.sh --list --zookeeper localhost:2181

# Check the log files (if configured in /usr/local/kafka/config/server.properties)
# ls /tmp/kafka-logs/demotopic1-0
```

#### 3\. Produce Messages

Start the console producer and type messages into the terminal. Each line sent will be a separate message.

```bash
kafka-console-producer.sh --broker-list localhost:9092 --topic demotopic1
```

#### 4\. Start a Consumer (Consume from Beginning)

Start the console consumer in a **new terminal**. The `--from-beginning` flag ensures it reads all existing messages.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic demotopic1 --from-beginning
```

#### 5\. Start a Consumer (Incremental Logs Only)

Start another console consumer in a **third terminal**. This consumer will only show new messages produced *after* it starts.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic demotopic1
```

*(You should now be able to type messages into the producer terminal and see them appear in both consumer terminals.)*

-----

### Part 2: Setting Up a Multi-Broker Cluster (3 Nodes)

To simulate a real cluster, we expand the single-node setup to three nodes running on the same machine (on different ports and log directories).

#### 1\. Clone Configuration Files

Create two new configuration files for the new brokers (broker ID 1 and 2).

```bash
cd /usr/local/kafka
cp config/server.properties config/server-1.properties
cp config/server.properties config/server-2.properties
```

#### 2\. Edit Configuration Files

Modify the unique properties for each new broker: `broker.id`, `listeners` (port), and `log.dir`.

| File | Property | Value |
| :--- | :--- | :--- |
| `config/server-1.properties` | `broker.id` | `1` |
| | `listeners` | `PLAINTEXT://:9093` |
| | `log.dir` | `/tmp/kafka-logs-1` |
| `config/server-2.properties` | `broker.id` | `2` |
| | `listeners` | `PLAINTEXT://:9094` |
| | `log.dir` | `/tmp/kafka-logs-2` |

#### 3\. Start the New Brokers

Start the two new broker nodes using their specific configuration files. (Assuming the original broker 0 on port 9092 is still running).

```bash
kafka-server-start.sh -daemon $KAFKA_HOME/config/server-1.properties
kafka-server-start.sh -daemon $KAFKA_HOME/config/server-2.properties
```

#### 4\. Create a Highly Replicated Topic

Create a new topic, `demotopic2`, with a **replication factor of 3**.

```bash
kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 3 --partitions 1 --topic demotopic2
kafka-topics.sh --list --zookeeper localhost:2181
```

#### 5\. Alter Topic Partitions

Alter the topic to increase the number of partitions from 1 to 3.

```bash
kafka-topics.sh --zookeeper localhost:2181 --alter --topic demotopic2 --partitions 3
```

#### 6\. Describe Topics to View Leadership and Replication

Use the `describe` command to see which brokers (0, 1, or 2) are the **Leader**, which are the **Replicas**, and which are the **In-Sync Replicas (ISRs)**.

```bash
kafka-topics.sh --describe --zookeeper localhost:2181 --topic demotopic2

# Example Output (Leadership distribution across partitions):
# Topic: demotopic2	PartitionCount:3	ReplicationFactor:3	Configs:
# Topic: demotopic2	Partition: 0	Leader: 1	Replicas: 0,1,2	Isr: 1,2,0
# Topic: demotopic2	Partition: 1	Leader: 1	Replicas: 1,2,0	Isr: 1,2,0
# Topic: demotopic2	Partition: 2	Leader: 2	Replicas: 2,0,1	Isr: 2,0,1

# BEST PRACTICE: The number of partitions should generally equal the number of brokers.
```

#### 7\. Describe the Original Topic

Run the same command on `demotopic1` to see where its single partition is located (it will only show one Leader and one Replica, which is itself, as its factor is 1).

```bash
kafka-topics.sh --describe --zookeeper localhost:2181 --topic demotopic1
```

#### 8\. Produce Messages to the Multi-Broker Topic

Publish messages to `demotopic2`, specifying all broker ports in the `--broker-list`.

```bash
kafka-console-producer.sh --broker-list localhost:9092,localhost:9093,localhost:9094 --topic demotopic2

# Note: Messages will be posted in ROUND ROBIN order to the PARTITIONS (which are hosted by the brokers).
```

#### 9\. Consume Messages from the Multi-Broker Topic

Start a consumer, specifying all broker ports in the `--bootstrap-server` list.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092,localhost:9093,localhost:9094 --topic demotopic2 --from-beginning
```

-----

### Part 3: Testing Fault Tolerance

#### 10\. Kill a Leader Broker

Broker 1 was acting as the leader for two partitions (0 and 1). Find its process ID and kill it.

```bash
ps -ef | grep server-1.properties
kill -9 [PID of broker 1] 
```

#### 11\. Describe Topics After Failure

Re-run the describe command. Note that the **Leader** for the affected partitions will have switched to another available broker (e.g., 0 or 2), and the failed broker (1) will be removed from the **Isr** list.

```bash
kafka-topics.sh --describe --zookeeper localhost:2181 --topic demotopic2
```

#### 12\. Verify Consumption After Failover

Attempt to consume the messages again. All messages should still be available, demonstrating fault tolerance.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092,localhost:9093,localhost:9094 --from-beginning --topic demotopic2
```

#### 13\. Delete the Topic

Mark the topic for deletion. Note that topic deletion must be enabled in the broker configuration (`delete.topic.enable=true`) for immediate removal.

```bash
kafka-topics.sh --delete --zookeeper localhost:2181 --topic demotopic2
```