## 📌 Kafka Topic Description – Terminology Explanation

### 🔹 Command Used

```bash
kafka-topics.sh --describe --zookeeper localhost:2181 --topic demotopic2
```

---

## 📊 Kafka Terminologies Explained

| **Term**                   | **Description**                                                                                                             |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Topic**                  | A logical category or feed name where Kafka stores messages. Producers write data to topics and consumers read from topics. |
| **demotopic2**             | Name of the Kafka topic being described.                                                                                    |
| **PartitionCount**         | Number of partitions the topic is divided into. Each partition allows parallelism and scalability.                          |
| **Partition**              | A single, ordered, immutable sequence of records within a topic. Each partition is stored on one or more brokers.           |
| **Partition 0 / 1 / 2**    | Unique partition IDs within the topic. Partition numbering starts from 0.                                                   |
| **ReplicationFactor**      | Number of copies of each partition maintained across different brokers for fault tolerance.                                 |
| **Leader**                 | The broker responsible for handling **all reads and writes** for a partition. Only one leader exists per partition.         |
| **Broker ID (0,1,2)**      | Unique numeric ID assigned to each Kafka broker in the cluster.                                                             |
| **Replicas**               | List of broker IDs that hold a copy of the partition data (includes leader + followers).                                    |
| **Follower Replica**       | Replicas that are not leaders. They replicate data from the leader.                                                         |
| **ISR (In-Sync Replicas)** | Subset of replicas that are fully synchronized with the leader and eligible to become leader if failure occurs.             |
| **Configs**                | Topic-level configuration parameters (empty here means default settings are applied).                                       |
| **ZooKeeper**              | Centralized service used (in older Kafka versions) to manage metadata, broker coordination, and leader election.            |

---

## 🔁 Partition-Level Explanation (Example)

| **Partition** | **Leader** | **Replicas** | **ISR** |
| ------------- | ---------- | ------------ | ------- |
| 0             | Broker 0   | 0,1,2        | 0,2,1   |
| 1             | Broker 1   | 1,2,0        | 1,2,0   |
| 2             | Broker 2   | 2,0,1        | 2,1,0   |

✔ **Leader handles traffic**
✔ **Replicas ensure fault tolerance**
✔ **ISR ensures high availability**

---

## 🧠 Key Notes

* **Higher partitions = higher parallelism**
* **Replication factor > 1 = fault tolerance**
* **Leader failure → new leader elected from ISR**
* **If a replica falls behind → removed from ISR**
* **Without ISR → data loss risk**

---
