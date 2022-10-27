#!/bin/bash

python3.8 main.py \
--dataset_name $DATASET_NAME \
--max_epochs $MAX_EPOCHS \
--per_gpu_batch_size $PER_GPU_BATCH_SIZE \
--db_name $DB_NAME \
--db_region $DB_REGION \