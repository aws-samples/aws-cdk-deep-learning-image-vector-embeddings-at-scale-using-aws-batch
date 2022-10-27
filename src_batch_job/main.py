import argparse
import json
import logging

import boto3
from datetime import datetime
from decimal import Decimal
from auto_mm_bench.vision_datasets import vision_dataset_registry as data
from autogluon.multimodal import MultiModalPredictor


def get_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="automm-cv-benchmark")
    parser.add_argument(
        "--dataset_name", type=str, help="Name of vision_dataset", default="nike"
    )
    parser.add_argument(
        "--max_epochs",
        type=int,
        help="The max training epochs in the training.",
        default=1,
    )
    parser.add_argument(
        "--per_gpu_batch_size", type=int, help="The batch size of each GPU.", default=32
    )
    parser.add_argument(
        "--db_name",
        type=str,
        help="DynamoDB to record results.",
        default="automm-cv-bench-dynamodb-table",
    )
    parser.add_argument(
        "--db_region",
        type=str,
        help="Region of DynamoDB",
        default="us-west-2",
    )
    args = parser.parse_args()
    return args


def write_db(table, args, score, time):
    item = {
        "dataset": args.dataset_name,
        "batch_size": args.per_gpu_batch_size,
        "max_epochs": args.max_epochs,
        "score": round(score, 3),
        "training_time": f"{int(time[0])}m{int(time[1])}s",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    item = json.loads(json.dumps(item), parse_float=Decimal)
    table.put_item(Item=item)


def get_db(db_name, db_region):
    dynamodb = boto3.resource("dynamodb", region_name=db_region)
    table = dynamodb.Table(db_name)
    return table


def main():
    args = get_args()
    table = get_db(args.db_name, args.db_region)

    # Default AutoMM, Swin-base model train 10 epochs
    hyperparameters = {
        "env.per_gpu_batch_size": args.per_gpu_batch_size,
        "optimization.max_epochs": args.max_epochs,
    }
    train_data = data.create(args.dataset_name, "train")
    test_data = data.create(args.dataset_name, "test")

    predictor = MultiModalPredictor(
        label=train_data.label_columns[0],
        problem_type=train_data.problem_type,
        eval_metric=train_data.metric,
    )

    start_time = datetime.now()
    predictor.fit(
        train_data=train_data.data,
        tuning_data=train_data.data
        if args.dataset_name in ["bijou_dogs", "redfin"]
        else None,  # hacky solution for fewshot datasets: bijou_dogs, redfin
        hyperparameters=hyperparameters,
    )
    end_time = datetime.now()
    elapsed_seconds = (end_time - start_time).total_seconds()
    elapsed_min = divmod(elapsed_seconds, 60)
    scores = predictor.evaluate(test_data.data, metrics=train_data.metric)
    logging.info("Top-1 test acc: %.3f" % scores[train_data.metric])
    write_db(table, args, scores[train_data.metric], elapsed_min)


if __name__ == "__main__":
    main()
