# Data

项目总览和完整复现步骤见根目录的 [README](../README.md)。

Download the official Tianchi User Behavior Data from
https://tianchi.aliyun.com/dataset/dataDetail?dataId=649 and save it locally as
`data/raw/UserBehavior.csv`.

The dataset fields are:

| Field | Description |
| --- | --- |
| `user_id` | Anonymized user identifier. |
| `item_id` | Item identifier. |
| `category_id` | Item category identifier. |
| `behavior_type` | User action: `pv`, `buy`, `cart`, or `fav`. |
| `timestamp` | Unix timestamp in seconds. |

Raw Tianchi data must not be committed to this repository. The small CSV in
`data/sample/` is synthetic and is provided only for local development and tests.
It must not be used to draw business conclusions or to stand in for a full-data
analysis.

After downloading the source file, keep it at `data/raw/UserBehavior.csv` and
run the root README's preparation command to produce the ignored local file
`data/processed/user_behavior_cleaned.csv`. Neither raw nor processed full-data
files belong in commits.
