# Candidate before-and-after examples - T2

One clean variant per topic, chosen for a visible text change. These are examples to inspect, not proven teaching improvements. The automated fidelity audit may miss errors.

## caching - chatgpt

Source ID: `7ac6680a-25b1-4216-b8d9-d58317d5e206`. Variant ID: `0398fa76-f4a2-4991-ab36-d5b57ce2d23f`. Automated word similarity: 0.979. Raw pipeline record: `transform-caching-chatgpt-T2.json`.

### Before

````markdown
Write-through and write-back are two cache write policies that determine when data is written to the cache and to the next level of memory (such as RAM or disk).

The main tradeoff is data consistency and simplicity vs. write performance.
1. Write-through cache
When the CPU writes data, the cache is updated, and the same data is immediately written to the next memory level.
CPU

Write data


Cache + Main Memory

Both are updated on the write


Example: Suppose the CPU changes a value from 10 to 20.
1. The cache value becomes 20.
2. Main memory is also updated to 20.
3. The write completes according to the system's memory-write acknowledgment rules.
Advantages
- Main memory stays up to date with the cache, assuming writes complete successfully.
- Simpler recovery and cache management.
- Less risk of losing the latest value if the cache is discarded, provided the memory write has completed.
Disadvantages
- Every write generates a memory write.
- Higher write latency if the CPU must wait for the lower-level memory.
- Greater memory-bus traffic.
A write buffer can reduce the CPU's waiting time, although the memory write still needs to happen.
2. Write-back cache
When the CPU writes data, only the cache is updated initially. Main memory is updated later, usually when the modified cache block is evicted.
CPU

Write data


Cache

Updated immediately; block marked dirty


Main Memory

Updated later when the dirty block is written back


Example: Suppose the CPU changes a value from 10 to 20.
1. The cache value becomes 20.
2. Main memory remains at 10 temporarily.
3. The cache marks the block as dirty, indicating that it has been modified.
4. When that block is evicted, the modified data is written to main memory.
If the same cache block is written five times before eviction, the system may need only one write-back of that block instead of five separate memory writes.

Advantages
- Faster writes in the common case.
- Fewer writes to lower-level memory.
- Reduced memory-bus traffic, especially when the same cache block is modified repeatedly.
Disadvantages
- Main memory may contain stale data while a dirty block remains in the cache.
- Evicting a dirty block requires a write-back, which can cause a delay.
- Cache coherence, recovery, and data-loss handling are more complex.
3. Side-by-side comparison
Feature	Write-through	Write-back
Cache updated on write	Immediately	Immediately
Main memory updated	On each write	Later, on write-back
Write latency	Generally higher	Generally lower
Memory traffic	Higher	Lower
Dirty bit required	Not for this policy alone	Yes, typically
Implementation	Simpler	More complex
Main memory consistency	More up to date after completed writes	May be stale
Repeated writes to same block	Each write propagates	Can be combined into one write-back

4. A quick numerical example
Suppose the CPU writes to the same cache block 100 times before it is evicted.
Write-through
100 writes



100 lower-level write operations, assuming each write propagates separately.

Write-back
1 write-back



One lower-level write-back if the block is eventually evicted while dirty.


This is an illustrative example, not a universal performance ratio. Actual traffic depends on write buffers, cache-line size, eviction behavior, and memory-system design.
5. When should each be used?
- Write-through: Appropriate when simpler consistency behavior is valuable, or when lower-level writes are inexpensive and predictable.
- Write-back: Common in CPU caches because it reduces memory traffic and improves write performance.
One important distinction: write-through does not automatically mean durable storage. A write reaching RAM, for example, does not guarantee that it has been persisted to disk.

Exam tip: Remember these two phrases:
- Write-through = update cache and memory together.
- Write-back = update cache now, write memory back later.











You're using the free version of ChatGPT. Upgrade for advanced models, better memory, and higher-quality image creation.
````

### After

````markdown
Write-through and write-back are two cache write policies that determine when data is written to the cache and to the next level of memory (such as RAM or disk).

The main tradeoff is data consistency and simplicity vs. write performance.

1. Write-through cache
When the CPU writes data, the cache is updated, and the same data is immediately written to the next memory level.
CPU

Write data


Cache + Main Memory

Both are updated on the write


Example: Suppose the CPU changes a value from 10 to 20.
1. The cache value becomes 20.
2. Main memory is also updated to 20.
3. The write completes according to the system's memory-write acknowledgment rules.
Advantages
- Main memory stays up to date with the cache, assuming writes complete successfully.
- Simpler recovery and cache management.
- Less risk of losing the latest value if the cache is discarded, provided the memory write has completed.
Disadvantages
- Every write generates a memory write.
- Higher write latency if the CPU must wait for the lower-level memory.
- Greater memory-bus traffic.
A write buffer can reduce the CPU's waiting time, although the memory write still needs to happen.

2. Write-back cache
Now that write-through is in place, write-back follows: when the CPU writes data, only the cache is updated initially. Main memory is updated later, usually when the modified cache block is evicted.
CPU

Write data


Cache

Updated immediately; block marked dirty


Main Memory

Updated later when the dirty block is written back


Example: Suppose the CPU changes a value from 10 to 20.
1. The cache value becomes 20.
2. Main memory remains at 10 temporarily.
3. The cache marks the block as dirty, indicating that it has been modified.
4. When that block is evicted, the modified data is written to main memory.
If the same cache block is written five times before eviction, the system may need only one write-back of that block instead of five separate memory writes.

Advantages
- Faster writes in the common case.
- Fewer writes to lower-level memory.
- Reduced memory-bus traffic, especially when the same cache block is modified repeatedly.
Disadvantages
- Main memory may contain stale data while a dirty block remains in the cache.
- Evicting a dirty block requires a write-back, which can cause a delay.
- Cache coherence, recovery, and data-loss handling are more complex.

3. Side-by-side comparison
Feature	Write-through	Write-back
Cache updated on write	Immediately	Immediately
Main memory updated	On each write	Later, on write-back
Write latency	Generally higher	Generally lower
Memory traffic	Higher	Lower
Dirty bit required	Not for this policy alone	Yes, typically
Implementation	Simpler	More complex
Main memory consistency	More up to date after completed writes	May be stale
Repeated writes to same block	Each write propagates	Can be combined into one write-back

4. A quick numerical example
Suppose the CPU writes to the same cache block 100 times before it is evicted.
Write-through
100 writes



100 lower-level write operations, assuming each write propagates separately.

Write-back
1 write-back



One lower-level write-back if the block is eventually evicted while dirty.


This is an illustrative example, not a universal performance ratio. Actual traffic depends on write buffers, cache-line size, eviction behavior, and memory-system design.

5. When should each be used?
- Write-through: Appropriate when simpler consistency behavior is valuable, or when lower-level writes are inexpensive and predictable.
- Write-back: Common in CPU caches because it reduces memory traffic and improves write performance.
One important distinction: write-through does not automatically mean durable storage. A write reaching RAM, for example, does not guarantee that it has been persisted to disk.

Exam tip: Remember these two phrases:
- Write-through = update cache and memory together.
- Write-back = update cache now, write memory back later.
````

## databases - chatgpt

Source ID: `fe4b2942-b26f-4bc3-bef3-df0640e69137`. Variant ID: `75a65eec-d3a4-4575-8442-5e1e4b418544`. Automated word similarity: 1.000. Raw pipeline record: `transform-databases-chatgpt-T2.json`.

### Before

````markdown
A B-tree database index makes lookups faster by organizing keys in a balanced, sorted tree, so the database can find a record without scanning every row. The trade-off is additional storage and extra work whenever indexed data changes.
1. How a B-tree index speeds up a lookup
Imagine a database table containing 1,000,000 users, and you run this query:
SELECT * FROM users WHERE id = 782451;


Without an index: Full table scan
Check rows one by one

Row 1 → Row 2 → Row 3 → ... → Row 1,000,000

Worst case: examine all 1,000,000 rows.


For an unsorted table, the database may need to examine every row to find the matching ID. The lookup cost grows approximately linearly with the number of rows: \(O(n)\).
With a B-tree index
Root node

Keys: 300,000 · 600,000 · 900,000

Internal node

600,000–900,000


Internal node

750,000–800,000



Leaf node

782,451 → row location (pointer)


Illustrative structure, not an exact index layout.

A B-tree node stores multiple sorted keys and references to child nodes. At each level, the database chooses the relevant range and follows the corresponding child pointer.

Because the tree stays balanced, its height grows logarithmically:
\[
\text{Lookup cost} = O(\log n)
\]

For example, a million entries might require only a handful of tree-level page accesses, rather than scanning a million rows. The actual number depends on the tree's branching factor, page layout, and caching.

Why it works: Each node eliminates large portions of the search space. A B-tree has a high branching factor, meaning one node can direct the search toward many possible ranges.
2. What does the index cost you?
There are four main costs.

1. Extra disk storage

The database must store the index's keys, child pointers, row references, and page structures in addition to the table itself.




2. Slower INSERT operations

When a new row is inserted, the database must insert its indexed key in the appropriate location. A page may split if it becomes full, requiring additional work.




3. Slower UPDATE and DELETE operations

Changing an indexed column may require index entries to be updated or relocated. Deleting a row also requires corresponding index maintenance.




4. Memory and maintenance overhead

Index pages consume buffer-cache memory when cached, and the database needs CPU and I/O for index traversal, maintenance, and sometimes rebuilding.



3. The trade-off in one table
Operation	Without index	With B-tree index
Find a specific row	Often \(O(n)\)	\(O(\log n)\) tree search
Insert a row	Insert into table	Insert into table and maintain index
Update indexed column	Update table	Update table and index
Delete a row	Delete from table	Delete from table and index
Storage	Lower	Higher

These are simplified comparisons. A query's actual performance also depends on selectivity, table organization, caching, and whether the index can satisfy the query without accessing the table.
4. When should you create an index?
Consider this table:
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    email VARCHAR(255),
    name VARCHAR(100)
);


A primary key normally has an index created automatically. If your application frequently looks up users by email, another index may help:
CREATE INDEX idx_users_email ON users(email);


Now this query can use the email index:
SELECT * FROM users WHERE email = 'user@example.com';


However, indexing every column is usually a mistake. Each additional index adds storage and write overhead, and a low-selectivity column may offer little benefit for some queries.

Practical rule: Index columns frequently used in selective WHERE conditions, joins, and relevant ORDER BY operations. Verify the benefit using EXPLAIN or your database's execution-plan tools.
The key idea
A B-tree index is a read-performance optimization purchased with storage and write-performance costs. It is most valuable when the speed gained by repeated lookups outweighs the overhead of maintaining the index.
````

### After

````markdown
A B-tree database index makes lookups faster by organizing keys in a balanced, sorted tree, so the database can find a record without scanning every row. The trade-off is additional storage and extra work whenever indexed data changes.
1. How a B-tree index speeds up a lookup
Imagine a database table containing 1,000,000 users, and you run this query:
SELECT * FROM users WHERE id = 782451;


Without an index: Full table scan
Check rows one by one

Row 1 → Row 2 → Row 3 → ... → Row 1,000,000

Worst case: examine all 1,000,000 rows.


For an unsorted table, the database may need to examine every row to find the matching ID. The lookup cost grows approximately linearly with the number of rows: \(O(n)\).
With a B-tree index
Root node

Keys: 300,000 · 600,000 · 900,000

Internal node

600,000–900,000


Internal node

750,000–800,000



Leaf node

782,451 → row location (pointer)


Illustrative structure, not an exact index layout.

A B-tree node stores multiple sorted keys and references to child nodes. At each level, the database chooses the relevant range and follows the corresponding child pointer.

Because the tree stays balanced, its height grows logarithmically:
\[
\text{Lookup cost} = O(\log n)
\]

For example, a million entries might require only a handful of tree-level page accesses, rather than scanning a million rows. The actual number depends on the tree's branching factor, page layout, and caching.

Why it works: Each node eliminates large portions of the search space. A B-tree has a high branching factor, meaning one node can direct the search toward many possible ranges.
2. What does the index cost you?
There are four main costs.

1. Extra disk storage

The database must store the index's keys, child pointers, row references, and page structures in addition to the table itself.




2. Slower INSERT operations

When a new row is inserted, the database must insert its indexed key in the appropriate location. A page may split if it becomes full, requiring additional work.




3. Slower UPDATE and DELETE operations

Changing an indexed column may require index entries to be updated or relocated. Deleting a row also requires corresponding index maintenance.




4. Memory and maintenance overhead

Index pages consume buffer-cache memory when cached, and the database needs CPU and I/O for index traversal, maintenance, and sometimes rebuilding.



3. The trade-off in one table
Operation	Without index	With B-tree index
Find a specific row	Often \(O(n)\)	\(O(\log n)\) tree search
Insert a row	Insert into table	Insert into table and maintain index
Update indexed column	Update table	Update table and index
Delete a row	Delete from table	Delete from table and index
Storage	Lower	Higher

These are simplified comparisons. A query's actual performance also depends on selectivity, table organization, caching, and whether the index can satisfy the query without accessing the table.
4. When should you create an index?
Consider this table:
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    email VARCHAR(255),
    name VARCHAR(100)
);


A primary key normally has an index created automatically. If your application frequently looks up users by email, another index may help:
CREATE INDEX idx_users_email ON users(email);


Now this query can use the email index:
SELECT * FROM users WHERE email = 'user@example.com';


However, indexing every column is usually a mistake. Each additional index adds storage and write overhead, and a low-selectivity column may offer little benefit for some queries.

Practical rule: Index columns frequently used in selective WHERE conditions, joins, and relevant ORDER BY operations. Verify the benefit using EXPLAIN or your database's execution-plan tools.
The key idea
A B-tree index is a read-performance optimization purchased with storage and write-performance costs. It is most valuable when the speed gained by repeated lookups outweighs the overhead of maintaining the index.
````

## tcp - claude

Source ID: `3cfaae4b-bf68-4beb-9eef-a00f8f92bce1`. Variant ID: `497782e3-bcd3-45a7-a4a6-6982604a205b`. Automated word similarity: 0.775. Raw pipeline record: `transform-tcp-claude-T2.json`.

### Before

````markdown
The three-way handshake lets two machines agree that both can send and receive, and agree on the starting sequence numbers TCP uses to order and acknowledge data.

The three steps

SYN (client → server): The client sends a segment with the SYN flag set and its own initial sequence number, say x. This says: “I want to open a connection, and my bytes will be numbered starting from x.”
SYN-ACK (server → client): The server replies with both SYN and ACK set. The ACK field is x+1, confirming it received the client’s SYN (a SYN consumes one sequence number). The segment also carries the server’s own initial sequence number, y. This says: “I got yours, and mine start at y.”
ACK (client → server): The client sends a segment with ACK set and acknowledgment number y+1. This says: “I got yours too.” The connection is now established, and data can flow in both directions (the third segment can already carry data).

Why each step is needed

TCP is full duplex, so each direction has its own sequence number space. For reliable delivery, each side must (a) announce its starting number and (b) have the other side confirm it. That’s four pieces of information: two SYNs and two ACKs. The server combines its ACK of the client’s SYN with its own SYN into one segment, which is why four messages collapse into three.

Step 1 is the only way the server learns that a client wants a connection, and it tells the server the client’s starting sequence number.
Step 2 proves to the client that the server is reachable and listening, that the client’s outgoing path works, and gives the server’s starting sequence number.
Step 3 proves to the server that the client can actually receive its packets, so the return path works. Without it, the server could not be sure its SYN-ACK arrived, and each side would not have confirmation that the other has agreed on its numbers.

Why not two steps?

Two steps would leave the server unsure the client ever received its sequence number. It also invites trouble with old, delayed duplicate SYNs. If a stale SYN from a past connection attempt arrives, the server would open a connection the client never wanted. With three steps, the client’s final ACK must carry y+1; if the client didn’t send the original SYN, it responds to the SYN-ACK with a reset (RST), and the server drops the half-open connection.

Why random initial sequence numbers?

Starting numbers are chosen unpredictably rather than at zero. This helps avoid confusion with segments from earlier connections between the same endpoints, and makes it harder for an attacker to forge packets by guessing sequence numbers.

A related weakness

Between steps 2 and 3 the server holds state for a half-open connection. SYN flood attacks exploit this by sending many SYNs and never completing the handshake. Defenses like SYN cookies avoid allocating state until the final ACK arrives.
````

### After

````markdown
To understand the three-way handshake, we first rely on the client-server model, network packets or segments, and reliable delivery, since establishing a connection ensures these mechanisms can proceed with agreed-upon parameters. Now that these foundational concepts are in place, the purpose of the mechanism follows: The three-way handshake lets two machines agree that both can send and receive, and agree on the starting sequence numbers TCP uses to order and acknowledge data.

TCP is full duplex, so each direction has its own sequence number space. For reliable delivery, each side must (a) announce its starting number and (b) have the other side confirm it. That’s four pieces of information: two SYNs and two ACKs. The server combines its ACK of the client’s SYN with its own SYN into one segment, which is why four messages collapse into three.

The three steps

SYN (client → server): The client sends a segment with the SYN flag set and its own initial sequence number, say x. This says: “I want to open a connection, and my bytes will be numbered starting from x.”
SYN-ACK (server → client): The server replies with both SYN and ACK set. The ACK field is x+1, confirming it received the client’s SYN (a SYN consumes one sequence number). The segment also carries the server’s own initial sequence number, y. This says: “I got yours, and mine start at y.”
ACK (client → server): The client sends a segment with ACK set and acknowledgment number y+1. This says: “I got yours too.” The connection is now established, and data can flow in both directions (the third segment can already carry data).

Now that the step-by-step breakdown is established, the necessity of each individual transmission becomes clear:

Step 1 is the only way the server learns that a client wants a connection, and it tells the server the client’s starting sequence number.
Step 2 proves to the client that the server is reachable and listening, that the client’s outgoing path works, and gives the server’s starting sequence number.
Step 3 proves to the server that the client can actually receive its packets, so the return path works. Without it, the server could not be sure its SYN-ACK arrived, and each side would not have confirmation that the other has agreed on its numbers.

With the three-step structure defined, we can examine why alternative designs are insufficient:

Why not two steps?

Two steps would leave the server unsure the client ever received its sequence number. It also invites trouble with old, delayed duplicate SYNs. If a stale SYN from a past connection attempt arrives, the server would open a connection the client never wanted. With three steps, the client’s final ACK must carry y+1; if the client didn’t send the original SYN, it responds to the SYN-ACK with a reset (RST), and the server drops the half-open connection.

Building upon how sequence numbers are utilized during connection establishment, we can look at how those values are selected:

Why random initial sequence numbers?

Starting numbers are chosen unpredictably rather than at zero. This helps avoid confusion with segments from earlier connections between the same endpoints, and makes it harder for an attacker to forge packets by guessing sequence numbers.

Finally, with the lifecycle of the handshake fully mapped, we can examine operational vulnerabilities associated with intermediate states:

A related weakness

Between steps 2 and 3 the server holds state for a half-open connection. SYN flood attacks exploit this by sending many SYNs and never completing the handshake. Defenses like SYN cookies avoid allocating state until the final ACK arrives.
````

## immunology - chatgpt

Source ID: `77fa0bb5-fe74-4069-b4ce-c01aed582d0f`. Variant ID: `8b8649cf-3149-42ea-8359-33764409b5de`. Automated word similarity: 0.813. Raw pipeline record: `transform-immunology-chatgpt-T2.json`.

### Before

````markdown
A vaccine trains your immune system by showing it a safe version or piece of a pathogen so it can learn to recognize and fight the real one later. The key is that your immune system can learn to recognize a pathogen without needing to experience the full disease it causes.
1. First, understand the problem
Your immune system protects you against pathogens such as viruses and bacteria. But it cannot immediately recognize every new pathogen.

A pathogen has distinctive molecules called antigens. Think of an antigen as an identifying feature that the immune system can learn to recognize.

When a new pathogen enters your body, your immune system must identify it, activate the right immune cells, and build a targeted defense. This takes time—which is why you can become sick during a first infection.
2. How a vaccine trains your immune system









Step 1: The vaccine introduces a safe target

Depending on the vaccine, it may contain a harmless piece of a pathogen, an inactivated pathogen, a weakened pathogen, or instructions for your cells to temporarily produce a pathogen protein.












Step 2: Immune cells identify the antigen

Specialized cells, such as dendritic cells, capture the antigen and present its fragments to T cells. This helps activate the specific immune responses needed to fight that pathogen.












Step 3: The immune system builds a targeted defense

Activated B cells can develop into plasma cells that produce antibodies. Antibodies bind to specific antigens and may block a virus from entering cells or help other immune components eliminate the threat.












Step 4: The immune system remembers

Some activated B and T cells become long-lived memory cells. If the real pathogen enters later, these cells help the immune system respond more quickly and effectively.



3. Why doesn't the vaccine cause the disease?
The answer depends on how the vaccine is made.
Vaccine type	How it avoids causing the disease
Inactivated	Uses a pathogen that has been killed and cannot reproduce.
Subunit	Uses only selected parts of the pathogen, not the whole infectious agent.
mRNA	Gives cells temporary instructions to make a pathogen protein, rather than the complete pathogen.
Live attenuated	Uses a weakened pathogen that is much less capable of causing disease in people with normal immune function, though it is unsuitable for some people.

These approaches expose the immune system to the information it needs to learn, while avoiding the dangers of a typical infection. No vaccine is entirely risk-free, and some vaccines are unsuitable for people with particular medical conditions.
4. What happens when the real pathogen arrives?
Without prior vaccination

The immune system must recognize the threat and develop a targeted response. The delay gives the pathogen time to multiply and cause illness.



After effective vaccination

Antibodies and memory cells can recognize the threat sooner, helping control the infection before it causes serious illness.



Vaccination does not always prevent infection completely. Protection varies by vaccine and pathogen, but many vaccines substantially reduce the risk of severe disease.
5. The deeper idea: immunological memory
The immune system does not simply memorize a pathogen as a whole. It develops populations of antigen-specific B and T cells, some of which persist long after vaccination.

This is called adaptive immunity. It is specific to particular antigens and can respond more rapidly upon re-exposure.

Think of it like a security system: a vaccine gives the system a safe sample of a known intruder. The system learns what to look for, prepares its defenses, and can react faster if the real intruder appears.

The central principle: a vaccine lets the immune system practice recognizing a threat without requiring the body to undergo the full disease first.
````

### After

````markdown
A vaccine trains your immune system by showing it a safe version or piece of a pathogen so it can learn to recognize and fight the real one later. The key is that your immune system can learn to recognize a pathogen without needing to experience the full disease it causes.
1. First, understand the problem
Your immune system protects you against pathogens such as viruses and bacteria. But it cannot immediately recognize every new pathogen.

A pathogen has distinctive molecules called antigens. Think of an antigen as an identifying feature that the immune system can learn to recognize.

When a new pathogen enters your body, your immune system must identify it, activate the right immune cells, and build a targeted defense. This takes time—which is why you can become sick during a first infection.
2. How a vaccine trains your immune system









Step 1: The vaccine introduces a safe target

Depending on the vaccine, it may contain a harmless piece of a pathogen, an inactivated pathogen, a weakened pathogen, or instructions for your cells to temporarily produce a pathogen protein.












Step 2: Immune cells identify the antigen

Specialized cells, such as dendritic cells, capture the antigen and present its fragments to T cells. This helps activate the specific immune responses needed to fight that pathogen.












Step 3: The immune system builds a targeted defense

Activated B cells can develop into plasma cells that produce antibodies. Antibodies bind to specific antigens and may block a virus from entering cells or help other immune components eliminate the threat.












Step 4: The immune system remembers

Some activated B and T cells become long-lived memory cells. If the real pathogen enters later, these cells help the immune system respond more quickly and effectively.



3. The deeper idea: immunological memory
The immune system does not simply memorize a pathogen as a whole. It develops populations of antigen-specific B and T cells, some of which persist long after vaccination.

This is called adaptive immunity. It is specific to particular antigens and can respond more rapidly upon re-exposure.

Think of it like a security system: a vaccine gives the system a safe sample of a known intruder. The system learns what to look for, prepares its defenses, and can react faster if the real intruder appears.

The central principle: a vaccine lets the immune system practice recognizing a threat without requiring the body to undergo the full disease first.
4. Why doesn't the vaccine cause the disease?
The answer depends on how the vaccine is made.
Vaccine type	How it avoids causing the disease
Inactivated	Uses a pathogen that has been killed and cannot reproduce.
Subunit	Uses only selected parts of the pathogen, not the whole infectious agent.
mRNA	Gives cells temporary instructions to make a pathogen protein, rather than the complete pathogen.
Live attenuated	Uses a weakened pathogen that is much less capable of causing disease in people with normal immune function, though it is unsuitable for some people.

These approaches expose the immune system to the information it needs to learn, while avoiding the dangers of a typical infection. No vaccine is entirely risk-free, and some vaccines are unsuitable for people with particular medical conditions.
5. What happens when the real pathogen arrives?
Without prior vaccination

The immune system must recognize the threat and develop a targeted response. The delay gives the pathogen time to multiply and cause illness.



After effective vaccination

Antibodies and memory cells can recognize the threat sooner, helping control the infection before it causes serious illness.



Vaccination does not always prevent infection completely. Protection varies by vaccine and pathogen, but many vaccines substantially reduce the risk of severe disease.
````

## interest - claude

Source ID: `1183e608-2143-4cc2-b81e-0755c4fc29cf`. Variant ID: `0a31de56-9c29-4a4f-bb13-6412dbc164d0`. Automated word similarity: 0.923. Raw pipeline record: `transform-interest-claude-T2.json`.

### Before

````markdown
Simple interest is calculated only on your original amount (the principal). Compound interest is calculated on the principal plus all the interest you’ve already earned, so interest earns interest.

A quick example: $1,000 at 5% per year.

Simple interest: you earn $50 every year, always 5% of the original $1,000. After 10 years: $1,000 + $500 = $1,500.
Compound interest (annual): year 1 you earn $50, but in year 2 you earn 5% of $1,050 = $52.50, in year 3 5% of $1,102.50 = $55.13, and so on. After 10 years: $1,000 × 1.05¹⁰ ≈ $1,629.

The formulas:

Simple: A = P(1 + rt)
Compound: A = P(1 + r/n)^(nt), where n is how many times per year interest is compounded

Why the gap grows over time:

Simple interest grows by the same fixed amount each period, which is a straight line. Compound interest grows by a fixed percentage of an ever-larger balance, which is an exponential curve.

In the early years the two are nearly identical, because there’s little accumulated interest to earn interest on. The gap in year 2 is just 5% of the $50 earned in year 1, or $2.50. But each year the compounding base is larger, so each year’s “interest on interest” is larger, and that extra amount itself starts earning more interest. The difference between the two isn’t just growing, it’s growing at an accelerating rate.

You can see it in the 10-year numbers above: the gap is $129. Stretch it to 30 years and simple interest gives $2,500, while compound gives about $4,322, a gap of over $1,800.

Things that widen the gap further:

A higher interest rate
Longer time horizons
More frequent compounding (monthly vs. annually), though this effect is smaller than rate and time

This is why compounding works in your favor on savings and investments, and against you on debt like credit cards, where unpaid interest gets added to the balance and starts accruing interest itself.
````

### After

````markdown
Simple interest is calculated only on your original amount (the principal). 

The formulas:

Simple: A = P(1 + rt)
Compound: A = P(1 + r/n)^(nt), where n is how many times per year interest is compounded

Compound interest is calculated on the principal plus all the interest you’ve already earned, so interest earns interest.

A quick example: $1,000 at 5% per year.

Simple interest: you earn $50 every year, always 5% of the original $1,000. After 10 years: $1,000 + $500 = $1,500.
Compound interest (annual): year 1 you earn $50, but in year 2 you earn 5% of $1,050 = $52.50, in year 3 5% of $1,102.50 = $55.13, and so on. After 10 years: $1,000 × 1.05¹⁰ ≈ $1,629.

Why the gap grows over time:

Simple interest grows by the same fixed amount each period, which is a straight line. Compound interest grows by a fixed percentage of an ever-larger balance, which is an exponential curve.

In the early years the two are nearly identical, because there’s little accumulated interest to earn interest on. The gap in year 2 is just 5% of the $50 earned in year 1, or $2.50. But each year the compounding base is larger, so each year’s “interest on interest” is larger, and that extra amount itself starts earning more interest. The difference between the two isn’t just growing, it’s growing at an accelerating rate.

You can see it in the 10-year numbers above: the gap is $129. Stretch it to 30 years and simple interest gives $2,500, while compound gives about $4,322, a gap of over $1,800.

Things that widen the gap further:

A higher interest rate
Longer time horizons
More frequent compounding (monthly vs. annually), though this effect is smaller than rate and time

This is why compounding works in your favor on savings and investments, and against you on debt like credit cards, where unpaid interest gets added to the balance and starts accruing interest itself.
````
