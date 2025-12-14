## 🚀 Apache Kafka Hands-On Workouts

This is a detailed set of hands-on Kafka exercises covering single-broker setup, producing, consuming, and scaling up to a multi-broker cluster to test fault tolerance.

⚠️ Prerequisite Note: Setup Required!

Before attempting these workouts, you must go through the linked README file . The installation steps for Zookeeper and Kafka are mentioned there, and these services must be running locally before you execute any of the commands below.

### 🎯 **Part 1: Single Broker Setup & Basic Operations**

These steps establish the fundamental workflow of creating a topic, publishing, and consuming data in a single-node environment.

#### 1\. Topic Creation (1 Partition, 1 Replica) ➕

We use the `--zookeeper` flag to register the new topic, `demotopic1`.

```bash
kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 1 --partitions 1 --topic demotopic1
```

#### 2\. Verify Topic Existence 👀

Check the list of available topics.

```bash
kafka-topics.sh --list --zookeeper localhost:2181
```

> ⚙️ **Kafka Settings Location:** `/usr/local/kafka/config/server.properties`

#### 3\. Produce Messages (Send Data) ➡️

Start the producer console. Each line you type will be sent as a separate message to the topic.

```bash
kafka-console-producer.sh --broker-list localhost:9092 --topic demotopic1
```

#### 4\. Start Consumer (Read from Beginning) ⬅️

Open a **new terminal** and run the consumer. The `--from-beginning` flag ensures you see **all** messages, including those sent previously.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic demotopic1 --from-beginning 
```

#### 5\. Start Incremental Consumer (New Terminal) 🆕

Open a **third terminal**. This consumer will only show messages sent **after** it was started.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic demotopic1 
```

-----

### 🏗️ **Part 2: Scaling to a Multi-Broker Cluster (3 Nodes)**

We expand the cluster from one node to three (using different ports/directories on the same machine) to enable replication and fault tolerance.

#### 1\. Clone Configuration Files 📁

Duplicate the default configuration file for brokers 1 and 2.

```bash
cd /usr/local/kafka
cp config/server.properties config/server-1.properties
cp config/server.properties config/server-2.properties
```

#### 2\. Edit Configuration Files (Unique IDs & Ports) ✏️

Crucially, each broker needs a unique ID, port, and log directory.

| Broker | Property | Value |
| :--- | :--- | :--- |
| `server-1.properties` | `broker.id` | `1` |
| | `listeners` | `PLAINTEXT://:9093` |
| | `log.dir` | `/tmp/kafka-logs-1` |
| `server-2.properties` | `broker.id` | `2` |
| | `listeners` | `PLAINTEXT://:9094` |
| | `log.dir` | `/tmp/kafka-logs-2` |

#### 3\. Start the New Broker Nodes ▶️

Start the two new brokers using their customized config files.

```bash
kafka-server-start.sh -daemon $KAFKA_HOME/config/server-1.properties
kafka-server-start.sh -daemon $KAFKA_HOME/config/server-2.properties
```

#### 4\. Create a Highly Replicated Topic (Replication=3) 🛡️

Create `demotopic2` with a replication factor equal to the cluster size (3).

```bash
kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 3 --partitions 1 --topic demotopic2
kafka-topics.sh --list --zookeeper localhost:2181
```

#### 5\. Alter Topic Partitions (Scaling) ⏫

Increase the number of partitions to 3.

```bash
kafka-topics.sh --zookeeper localhost:2181 --alter --topic demotopic2 --partitions 3
```

#### 6\. Describe Topic Status (Leaders, ISRs) 📊

View the leader election and replication status across the brokers (0, 1, 2).

```bash
kafka-topics.sh --describe --zookeeper localhost:2181 --topic demotopic2

# Output shows which broker is the Leader for each partition (0, 1, 2)
# and which brokers are the In-Sync Replicas (Isr).

# 💡 BEST PRACTICE: NO OF PARTITIONS = NO OF BROKERS
```

#### 8\. Publish to Multi-Broker Topic (Round Robin) ➡️

Send messages, listing all available brokers in the `--broker-list`.

```bash
kafka-console-producer.sh --broker-list localhost:9092,localhost:9093,localhost:9094 --topic demotopic2

# Note: MESSAGES will be posted in ROUND ROBIN order to the PARTITIONS.
```

#### 9\. Consume from Multi-Broker Topic ⬅️

Consume messages, listing all bootstrap servers.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092,localhost:9093,localhost:9094 --topic demotopic2 --from-beginning
```

-----

### 💔 **Part 3: Testing Fault Tolerance**

#### 10\. Kill the Leader Broker 🛑

Identify and kill the process of one of the leader brokers (e.g., broker 1).

```bash
ps -ef | grep server-1.properties
kill -9 [PID] 
```

#### 11\. Verify Leadership Switch 🔄

Re-describe the topic. A new Leader will have been automatically elected from the remaining In-Sync Replicas (ISRs). The failed broker (1) will be removed from the ISR list.

```bash
kafka-topics.sh --describe --zookeeper localhost:2181 --topic demotopic2
```

#### 12\. Confirm Message Availability ✅

Verify that consumption still works, proving the cluster's fault tolerance despite the leader node failure.

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092,localhost:9093,localhost:9094 --from-beginning --topic demotopic2
```

#### 13\. Delete the Topic (Cleanup) 🗑️

Mark the topic for deletion.

```bash
kafka-topics.sh --delete --zookeeper localhost:2181 --topic demotopic2
```